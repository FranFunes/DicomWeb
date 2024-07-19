import ipaddress, psutil, logging, os, json
from shutil import copytree, rmtree, make_archive
from datetime import datetime, timedelta
from pydicom.multival import MultiValue

from sqlalchemy.exc import OperationalError

from flask import render_template, request, jsonify, send_file
from app_pkg import application, db
from app_pkg.aux_funcs import read_dataset, find_imgs_in_field, ping, zip_files
from app_pkg.db_models import Study, Series, Device, Filter

from services.dicom_interface import DicomInterface
from services import task_manager, check_storage_manager, store_scp

logger = logging.getLogger('__main__')

@application.route('/')
@application.route('/index')
@application.route('/queryRetrieve')
def query_retrieve():    
    return render_template('queryRetrieve.html')

@application.route('/search_studies', methods = ['GET','POST'])
def search_studies():

    # Get device info from database
    try:
        device = Device.query.get(request.json['device'])
        assert device
        logger.info('device found on database')
    except AssertionError:
        logger.info('device not found on database')
        return jsonify(message = "El dispositivo no existe"), 500
    except Exception as e:
        logger.info('uknwown error when reading device from database')
        logger.info(repr(e))
        return jsonify(message = "Error al leer la base de datos"), 500    
    
    # Parse and format study dates
    date_selector = request.json['dateSelector']
    if date_selector == 'anydate':
        studydate = ''
    elif date_selector == 'today':
        studydate = datetime.today().strftime('%Y%m%d')
    elif date_selector == 'yesterday':
        studydate = (datetime.today() - timedelta(days=1)).strftime('%Y%m%d')
    elif date_selector == 'day':
        studydate = datetime.strptime(request.json['startDate'], '%Y-%m-%d').strftime('%Y%m%d')
    else:
        start_date = datetime.strptime(request.json['startDate'], '%Y-%m-%d')        
        end_date = datetime.strptime(request.json['endDate'], '%Y-%m-%d')
        if start_date > end_date:
            end_date = start_date
        studydate = start_date.strftime('%Y%m%d')+'-'+end_date.strftime('%Y%m%d')

    # Get modalities from request
    modalities = request.json['modalities']
    # Get search field and value
    search_field = request.json['searchField']
    search_value = request.json['searchValue']

    # Build the data for the dicom query
    qr = {'StudyDate':  studydate}    
    if len(modalities) > 0:
        qr['ModalitiesInStudy'] = modalities
    if search_value:
        qr[search_field] = search_value
    rs = {'PatientName':'',
            'PatientID': '',
            'StudyTime': '',
            'ModalitiesInStudy':  '',
            'StudyDescription': '',
            device.imgs_study: ''}

    # Send the dicom query
    device_dict = {attr:getattr(device, attr) for attr in ["ae_title","port","address"]}
    ae = DicomInterface(ae_title = Device.query.get('__local_store_SCP__').ae_title, 
                        address = Device.query.get('__local_store_SCP__').address,
                        acse_timeout=120)    
    responses = ae.query_studies_in_device(device_dict, qr, rs)
    logger.debug(f'{len(responses)} studies found on {device.ae_title}')
    
    ae.release_connections()

    # Extract data from datasets
    full_data = []
    for study in responses:

        data = read_dataset(study, ['PatientName','PatientID','StudyDate','StudyTime','ModalitiesInStudy','StudyDescription',device.imgs_study,'StudyInstanceUID'],
                             field_names = {device.imgs_study:'ImgsStudy'},
                             fields_handlers = {'PatientName': lambda x: str(x.value),
                                                'ModalitiesInStudy': lambda x: '/'.join(x.value) if type(x.value) == MultiValue else x.value})  
        
        data['source'] = request.json['device']
        data['level'] = 'STUDY'
        full_data.append(data)    
    data = {
        "data": full_data
    }
        
    return data

@application.route('/local')
def local():
    return render_template('local.html')
                           
@application.route('/get_local_studies', methods = ['GET','POST'])
def get_local_studies():

    try:
        studies = Study.query.all()
        logger.debug(f'{len(studies)} studies found on local database')
    except Exception as e:
        logger.error(f'An error ocurred during database query')
        logger.error(repr(e))
        return jsonify(message = "An error ocurred during database query"), 500

    # Extract data from datasets
    full_data = []
    for study in Study.query.all():
        data = {}
        data['PatientName'] = study.patient.PatientName
        data['PatientID'] = study.patient.PatientID
        data['StudyDate'] = study.StudyDate.strftime('%d/%m/%y')
        data['StudyTime'] = study.StudyDate.strftime('%H:%M:%S')
        data['ModalitiesInStudy'] = '/'.join(set([ss.Modality for ss in study.series.all()]))
        data['StudyDescription'] = study.StudyDescription
        data['ImgsStudy'] = len(study.instances.all())
        data['StudyInstanceUID'] = study.StudyInstanceUID        
        data['source'] = 'local'
        data['level'] = 'STUDY'
        full_data.append(data)    

    data = {
        "data": full_data
    }

    return data

@application.route('/get_local_study_data', methods=['GET', 'POST'])
def get_local_study_data():
    
    try:
        study = Study.query.get(request.json['StudyInstanceUID'])
        logger.debug(f"Study {request.json['StudyInstanceUID']} found on local database")
    except Exception as e:
        logger.error(f'An error ocurred during database query')
        logger.error(repr(e))
        return jsonify(message = "An error ocurred during database query"), 500
    
    full_data = []
    for series in study.series.all():
        data = {
            'SeriesNumber': series.SeriesNumber,
            'SeriesDate': series.SeriesDate.strftime('%d/%m/%y'),
            'SeriesTime': series.SeriesDate.strftime('%H:%M:%S'),
            'Modality': series.Modality,
            'SeriesDescription': series.SeriesDescription,
            'ImgsSeries': len(series.instances.all()),
            'SeriesInstanceUID': series.SeriesInstanceUID,
        }           
            
        # Add study data
        data.update(request.json)         
        data['level'] = 'SERIES'
        full_data.append(data)
    
    data = {
        "data": full_data
    }
    
    return data

@application.route('/delete_studies', methods=['GET', 'POST'])
def delete_studies():
    
    # Get items to delete (remove repeated ones)
    items = request.json
    studies_uids = [ds['StudyInstanceUID'] for ds in items if ds['level'] == 'STUDY']
    items = list(filter(lambda x: not (x['level'] == 'SERIES' and x['StudyInstanceUID'] in studies_uids), items))

    success = 0
    for item in items:
        try:
            if item['level'] == 'STUDY':
                element = Study.query.get(item['StudyInstanceUID'])
            elif item['level'] == 'SERIES':
                element = Series.query.get(item['SeriesInstanceUID'])            
            path = element.path
            db.session.delete(element)                
            logger.debug(f"deleted {element}")
            success += 1
        except Exception as e:
            logger.error(f"an error ocurred deleting {item}")
            logger.error(repr(e))

    try:
        db.session.commit()     
        rmtree(path)       
        return jsonify(message = f"{success} deleted succesfully"), 200
    except Exception as e:
        logger.error(repr(e))         
        return jsonify(message = f"error al escribir en la base de datos"), 500
    
@application.route('/download_studies', methods=['GET', 'POST'])
def download_studies():
    
    # Get items to download
    items = request.json
    studies_uids = [ds['StudyInstanceUID'] for ds in items if ds['level'] == 'STUDY']
    items = list(filter(lambda x: not (x['level'] == 'SERIES' and x['StudyInstanceUID'] in studies_uids), items))
    
    # Zip files
    os.makedirs('app_pkg/dicomtemp', exist_ok=True)
    for item in items:
        if item['level'] == 'STUDY':
            element = Study.query.get(item['StudyInstanceUID'])
        elif item['level'] == 'SERIES':
            element = Series.query.get(item['SeriesInstanceUID'])    
        copytree(element.path, os.path.join('app_pkg/dicomtemp', os.path.basename(element.path)))
    make_archive('app_pkg/dicoms', 'zip', 'app_pkg/dicomtemp')    
    rmtree('app_pkg/dicomtemp')
    return jsonify(message = "Listo para descargar"), 200

@application.route('/download_zip')
def download_zip():
    return send_file('dicoms.zip', as_attachment = True)

@application.route('/get_study_data', methods=['GET', 'POST'])
def get_study_data():
    
    # Get device info from database
    try:
        device = Device.query.get(request.json['source'])
        assert device
    except AssertionError:
        logger.error(f'device not found in database')        
        return jsonify(message = "El dispositivo no existe"), 500
    except Exception as e:
        logger.error(f'unknown error ocurred when reading database')
        logger.error(repr(e))
        return jsonify(message = "Error al leer la base de datos"), 500
    
    # Build the data for the dicom query
    rs = {'SeriesNumber':'',
          'SeriesDate': '',
          'SeriesTime': '',
          'SeriesDescription': '',
          'Modality':'',
          device.imgs_series: ''}
          
    # Send the dicom query
    device_dict = {attr:getattr(device, attr) for attr in ["ae_title","port","address"]}
    ae = DicomInterface(ae_title = Device.query.get('__local_store_SCP__').ae_title, 
                        address = Device.query.get('__local_store_SCP__').address,
                        acse_timeout=120)
    responses = ae.query_series_in_study(device_dict, request.json['StudyInstanceUID'], responses = rs)
    logger.debug(f'{len(responses)} studies found on {device.ae_title}')
    ae.release_connections()
    
    # Extract data from datasets
    full_data = []
    for series in responses:
        data = read_dataset(series, ['SeriesNumber','SeriesDate','SeriesTime','Modality','SeriesDescription',device.imgs_series,'SeriesInstanceUID'],
                            field_names = {device.imgs_series:'ImgsSeries'},
                             default_value = '')
        # Add study data
        data.update(request.json)         
        data['level'] = 'SERIES'
        full_data.append(data)
    
    data = {
        "data": full_data
    }
    
    return data

@application.route('/get_devices')
def get_devices():
    
    try:
        devices = Device.query.all()
    except Exception as e:
        logger.error('Unknown error ocurred when searching devices in database')
        logger.error(repr(e))
        return jsonify(message = "Error al leer la base de datos"), 500

    devices = [{"name":d.name, "ae_title":d.ae_title, "address":d.address + ":" + str(d.port),
                "imgs_series": d.imgs_series, "imgs_study": d.imgs_study,                
                "filters" : [[key + item for key, item in json.loads(f.conditions).items()] for f in d.filters.all()]} 
               for d in devices if d.name!="__local_store_SCP__"]
    data = {
        "data": devices
    }

    return data

@application.route('/checkStorage')
def check_storage():    
    return render_template('checkStorage.html')

@application.route('/find_missing_series', methods = ['GET','POST'])
def find_missing_series():
        
    
    # Get device info from database
    try:
        device = Device.query.get(request.json['device'])
        assert device
    except AssertionError:
        logger.error('device not found')
        return jsonify(message = "El dispositivo no existe"), 500
    except Exception as e:
        logger.error('Unknown error ocurred when searching devices in database')
        logger.error(repr(e))
        return jsonify(message = "Error al leer la base de datos"), 500

    # Parse and format study dates
    date_selector = request.json['dateSelector']
    if date_selector == 'anydate':
        studydate = ''
    elif date_selector == 'today':
        studydate = datetime.today().strftime('%Y%m%d')
    elif date_selector == 'yesterday':
        studydate = (datetime.today() - timedelta(days=1)).strftime('%Y%m%d')
    elif date_selector == 'day':
        studydate = datetime.strptime(request.json['startDate'], '%Y-%m-%d').strftime('%Y%m%d')
    else:
        start_date = datetime.strptime(request.json['startDate'], '%Y-%m-%d')        
        end_date = datetime.strptime(request.json['endDate'], '%Y-%m-%d')
        if start_date > end_date:
            end_date = start_date
        studydate = start_date.strftime('%Y%m%d')+'-'+end_date.strftime('%Y%m%d')
    
    # Find missing series
    missing_series, archived_series, ignored_series = check_storage_manager.find_missing_series(request.json['device'], studydate)

    # Extract missing series data from datasets
    source = request.json['device']
    if source == 'CLOUDPACS':
        source = 'PACS'
    missing_series_data = []
    for ds in missing_series:
        ds_data = read_dataset(ds, ['PatientName','PatientID',
                                    'StudyDescription','StudyInstanceUID','StudyDate','StudyTime',
                                    'SeriesTime','SeriesNumber','Modality','SeriesDescription',device.imgs_series,'SeriesInstanceUID'],
                                    field_names = {device.imgs_series:'ImgsSeries'}, 
                                    default_value = '',
                                    fields_handlers = {'PatientName': lambda x: str(x.value)})
        ds_data['source'] = source
        ds_data['level'] = 'SERIES'
        missing_series_data.append(ds_data)   

    # Extract filtered series data from datasets
    ignored_series_data = []
    for ds in ignored_series:
        ds_data = read_dataset(ds, ['PatientName','PatientID',
                                    'StudyDescription','StudyInstanceUID','StudyDate','StudyTime',
                                    'SeriesTime','SeriesNumber','Modality','SeriesDescription',device.imgs_series,'SeriesInstanceUID'],
                                    field_names = {device.imgs_series:'ImgsSeries'}, 
                                    default_value = '',
                                    fields_handlers = {'PatientName': lambda x: str(x.value)})
        ds_data['source'] = source
        ds_data['level'] = 'SERIES'
        ignored_series_data.append(ds_data)   

    # Extract filtered series data from datasets
    archived_series_data = []
    for ds in archived_series:
        ds_data = read_dataset(ds, ['PatientName','PatientID',
                                    'StudyDescription','StudyInstanceUID','StudyDate','StudyTime',
                                    'SeriesTime','SeriesNumber','Modality','SeriesDescription',device.imgs_series,'SeriesInstanceUID'],
                                    field_names = {device.imgs_series:'ImgsSeries'}, 
                                    default_value = '',
                                    fields_handlers = {'PatientName': lambda x: str(x.value)})
        ds_data['source'] = source
        ds_data['level'] = 'SERIES'
        archived_series_data.append(ds_data) 
        
    data = {
        "data": missing_series_data,
        "ignored_series_data": ignored_series_data,
        "archived_series_data": archived_series_data,
        "device": request.json['device'],
    }
    
    return data

@application.route('/check_storage_progress')
def check_storage_progress():

    return {"data": {
        "status": check_storage_manager.status,
        "progress": f"{100*check_storage_manager.progress:.0f}%"
    }}

@application.route('/empty_table', methods = ['GET','POST'])
def empty_table():
    
    return {"data": ""}

@application.route('/tasks')
def tasks():
    return render_template('tasks.html')

@application.route('/get_tasks_table')
def get_tasks_table():

    data = task_manager.get_tasks_table()

    return {"data": data}

@application.route('/move', methods=['GET', 'POST'])
def move():       
    
    # Get destination ae_title from database
    dest = request.json['destination']
    if dest == 'Local':
        dest = '__local_store_SCP__'

    try:
        device = Device.query.get(dest)
        assert device
    except AssertionError:
        logger.error('device not found')
        return jsonify(message = "El dispositivo no existe"), 500
    except Exception as e:
        logger.error('uknown error when searching database')
        logger.error(repr(e))
        return jsonify(message = "Error al leer la base de datos"), 500      
    
    destination = device.ae_title 

    # Get items to send and remove repeated ones
    datasets = request.json['items']
    studies_uids = [ds['StudyInstanceUID'] for ds in datasets if ds['level'] == 'STUDY']
    datasets = list(filter(lambda x: not (x['level'] == 'SERIES' and x['StudyInstanceUID'] in studies_uids), datasets))
            
    # Send datasets 
    for task_data in datasets:
        task_data['destination'] = destination
        task_data['type'] = 'MOVE'
        task_manager.manage_task(action = 'new', task_data = task_data)

    return {"message": f"Se agregaron {len(datasets)} trabajos a la cola"}

@application.route('/send', methods=['GET', 'POST'])
def send():       
    
    # Get destination ae_title from database
    dest = request.json['destination']

    try:
        device = Device.query.get(dest)
        assert device
    except AssertionError:
        logger.error('device not found')
        return jsonify(message = "El dispositivo no existe"), 500
    except Exception as e:
        logger.error('uknown error when searching database')
        logger.error(repr(e))
        return jsonify(message = "Error al leer la base de datos"), 500      

    # Get items to send and remove repeated ones
    datasets = request.json['items']
    studies_uids = [ds['StudyInstanceUID'] for ds in datasets if ds['level'] == 'STUDY']
    datasets = list(filter(lambda x: not (x['level'] == 'SERIES' and x['StudyInstanceUID'] in studies_uids), datasets))
            
    # Send datasets 
    for task_data in datasets:
        task_data['destination'] = request.json['destination']
        task_data['type'] = 'SEND'
        task_data['datasets'] = datasets        
        task_manager.manage_task(action = 'new', task_data = task_data)

    return {"message": f"Se agregaron {len(datasets)} trabajos a la cola"}
    
@application.route('/task_action', methods=['GET', 'POST'])
def task_action():
    
    ids = request.json['ids']
    for task_id in ids:
        task_manager.manage_task(action = request.json['action'], task_id = task_id)
    return {"data": "success"}

@application.route('/manage_devices', methods=['GET', 'POST'])
def manage_devices():
    
    device_name = request.json["name"]
    ae_title = request.json["ae_title"]

    # Query database for device
    try:
        d = Device.query.get(device_name)
    except OperationalError as e:
        logger.error('SQL OperationalError')
        logger.error(repr(e))
        return jsonify(message = "Error al leer la base de datos"), 500    
           
    action = request.json["action"]
    if action == "delete":
        
        # Delete device 
        try:   
            assert d
            db.session.delete(d)
            db.session.commit()
            logger.info(f'device {d} deleted')
            return jsonify(message = "Dispositivo eliminado correctamente"), 200
        except AssertionError:
            logger.error('trying to delete unexistent device')
            return jsonify(message = "Error: el dispositivo no existe"), 500    
        except:
            logger.error('uknown error when searching database')
            logger.error(repr(e))
            return jsonify(message = "Error al leer la base de datos"), 500    
    
    
    # Check if IP is formatted correctly
    address = request.json["address"]
    try:
        ipaddress.ip_address(address)
    except ValueError:
        logger.info('IP address not formatted properly')
        return {"message":"Error: la dirección IP no es válida"}    
    
    # Check port
    port = request.json["port"]
    try:
        assert port.isnumeric()
        port = int(port)
    except:
        logger.info('invalid port')
        return {"message":"Error: el puerto no es válido"}    
            
    if action == "add":
        # Add new device        
        if d:
            logger.error('trying to create an already existent device') 
            return jsonify(message = "Error: el dispositivo ya existe"), 500    
        try:
            # Add device to database
            new_d = Device(name = device_name, ae_title = ae_title, address = address, port = port,
            imgs_series = request.json["imgs_series"] or "Unknown",
            imgs_study = request.json["imgs_study"] or "Unknown")
            db.session.add(new_d)
            db.session.commit()
            logger.info(f'device {new_d} created.') 
            return jsonify(message = "Dispositivo creado correctamente"), 200   
        except:
            logger.error('uknown error when creating new device')
            logger.error(repr(e))
            return jsonify(message = "Error al crear el nuevo dispositivo"), 500  
 
    # Edit device
    elif action == "edit":
        # Check if device exists
        if not d:
            logger.error('trying to edit an unexistent device') 
            return jsonify(message = "Error: el dispositivo no existe"), 500    
        
        # Edit device in database     
        try:       
            d.ae_title = ae_title
            d.address = address
            d.port = port
            d.imgs_series = request.json["imgs_series"] or "Unknown"
            d.imgs_study = request.json["imgs_study"] or "Unknown"
            db.session.commit()
            logger.info('device edited')
            return {"message":"Dispositivo editado correctamente"}    
        except Exception as e:
            logger.info('edit device failed')
            print(repr(e))
            return {"message":"Error al acceder a la base de datos"}

    
@application.route('/query_imgs_field', methods=['GET', 'POST'])
def query_imgs_field():
    
    device = request.json
    device["port"] = int(device["port"])
    field_names = find_imgs_in_field(device)
    
    return field_names

@application.route('/config')
def render_config():
    return render_template('config.html')

@application.route('/get_local_device')
def get_local_device():

    local = Device.query.get('__local_store_SCP__')
        
    # Get the IP address for each network interface available
    interfaces = psutil.net_if_addrs()
    stats = psutil.net_if_stats()
    ips = []
    for intface, addr_list in interfaces.items():
        if any(getattr(addr, 'address').startswith("169.254") for addr in addr_list):
            continue
        elif intface in stats and getattr(stats[intface], "isup"):
            [ips.append(addr.address) for addr in addr_list if addr.family.name =='AF_INET' and not addr.address=='127.0.0.1']
    
    addresses = '/'.join(ips)
    device = {'ae_title': local.ae_title, 'address': local.address, 'addresses': ips, 'port': local.port}

    data = {
        "data": device
    }

    return data

@application.route('/manage_local_device', methods=['GET', 'POST'])
def manage_local_device():        
    try:
        # Edit device in database
        local = Device.query.get('__local_store_SCP__')
        local.port = request.json['port']
        local.ae_title = request.json["ae_title"]
        local.address = request.json["address"]
    except:
        logger.error('Local device configuration could not be updated on the database')
        return jsonify(message = 'Local device configuration could not be updated on the database'), 500
    
    # Keep backup values for ae title and port
    old_aet = store_scp.ae_title
    old_port = store_scp.port
    old_address = store_scp.address

    # Restart DICOM interfaces
    try:
        # Set new values for ae title and port and restart store scp
        store_scp.stop_store_scp()
        store_scp.ae_title = request.json["ae_title"]
        store_scp.port = request.json['port']
        store_scp.address = request.json["address"]
        store_scp.start_store_scp()
        # If succesful, commit changes to database
        db.session.commit()
        return {"message":"Local DICOM interface configuration was updated successfully"} 
    except Exception as e:
        # If failed, rollback database changes and try to restart store scp with original attributes
        db.session.rollback()
        store_scp.ae_title = old_aet
        store_scp.port = old_port
        store_scp.address = old_address
        store_scp.start_store_scp()
        logger.error(repr(e))
        return jsonify(message = 'Local AET configuration could not be restarted with the selected configuration. Restoring previous values.'), 500

@application.route('/test_local_device', methods=['GET', 'POST'])
def test_local_device():   

    ae = DicomInterface(acse_timeout=120)  
    try:
        # Get local device info from database
        local = Device.query.get('__local_store_SCP__')
    except:
        logger.error('Database connection error')
        return jsonify(message = 'Local device configuration could not be read from the database'), 500

    device = {attr:getattr(local,attr) for attr in ['ae_title','port','address']}
    echo_response = ae.echo(device)
    if echo_response == 0:
        return jsonify(message = 'Local DICOM interface is up and running!!!'), 200
    else:
        return jsonify(message = 'Local DICOM interface is not running'), 200     

@application.route('/echo_remote_device', methods=['GET', 'POST'])
def echo_remote_device():       
    echo_response = store_scp.echo(request.json)
    if echo_response == 0:
        return jsonify(message = f"DICOM ECHO to {request.json['ae_title']}@{request.json['address']}:{request.json['port']} succesful"), 200
    else:
        return jsonify(message = f"DICOM ECHO to {request.json['ae_title']}@{request.json['address']}:{request.json['port']} failed"), 500  
       

@application.route('/ping_remote_device', methods=['GET', 'POST'])
def ping_remote_device():   

    ping_result = ping(request.json['address'], count = 2)
    if ping_result:
        return jsonify(message = request.json['address'] + ' is reacheable!!!'), 200
    else:
        return jsonify(message = request.json['address'] + ' is unreacheable!!!'), 500  

@application.route('/update_device_filters', methods=['GET', 'POST'])
def update_device_filters():   

    d = Device.query.get(request.json['device'])

    # Delete existent filters
    for f in d.filters.all():
        db.session.delete(f)

    # Append new filters to device
    for filter_data in request.json['filters']:        
        f = Filter(conditions = json.dumps(filter_data), device = d)
        if f.validate_conditions():
            db.session.add(f)
    db.session.commit()    

    return jsonify(message = 'Filters for ' + request.json['device'] + ' updated succesfully'), 200  