import json, ipaddress, os, psutil
from datetime import datetime, timedelta
from pydicom.multival import MultiValue

from flask import render_template, request, jsonify
from app_pkg import application, db
from app_pkg.aux_funcs import read_dataset, find_imgs_in_field
from app_pkg.dicom_interface import DicomInterface
from app_pkg.db_models import Patient, Study, Series, Instance, Device

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
    except AssertionError:
        return jsonify({"msg":"El dispositivo no existe"}, status = 500)
    except Exception as e:
        return jsonify({"msg":"Error al leer la base de datos"}, status = 500)    
    
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
            device['imgs_study']: ''}

    # Send the dicom query
    device_dict = {attr:getattr(device, attr) for attr in ["ae_title","port","address"]}
    ae = DicomInterface(ae_title = os.environ['STORE_SCP_AET'])    
    responses = ae.query_studies_in_device(device_dict, qr, rs)
    ae.release_connections()

    # Extract data from datasets
    full_data = []
    for study in responses:

        data = read_dataset(study, ['PatientName','PatientID','StudyDate','StudyTime','ModalitiesInStudy','StudyDescription',device['imgs_study'],'StudyInstanceUID'],
                             field_names = {device['imgs_study']:'ImgsStudy'},
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

    studies = Study.query.all()

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
    
    study = Study.query.get(request.json['StudyInstanceUID'])

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

@application.route('/get_study_data', methods=['GET', 'POST'])
def get_study_data():
    
    # Get device info from database
    try:
        device = Device.query.get(request.json['device'])
        assert device
    except AssertionError:
        return jsonify({"msg":"El dispositivo no existe"}, status = 500)
    except Exception as e:
        return jsonify({"msg":"Error al leer la base de datos"}, status = 500)      
    
    # Build the data for the dicom query
    rs = {'SeriesNumber':'',
          'SeriesDate': '',
          'SeriesTime': '',
          'SeriesDescription': '',
          'Modality':'',
          device['imgs_series']: ''}
          
    # Send the dicom query
    device_dict = {attr:getattr(device, attr) for attr in ["ae_title","port","address"]}
    ae = DicomInterface(ae_title = os.environ['STORE_SCP_AET'])
    responses = ae.query_series_in_study(device_dict, request.json['StudyInstanceUID'], responses = rs)
    ae.release_connections()
    
    # Extract data from datasets
    full_data = []
    for series in responses:
        data = read_dataset(series, ['SeriesNumber','SeriesDate','SeriesTime','Modality','SeriesDescription',device['imgs_series'],'SeriesInstanceUID'],
                            field_names = {device['imgs_series']:'ImgsSeries'},
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

    devices = Device.query.all()

    devices = [{"name":d.name, "ae_title":d.ae_title, "address":d.address + ":" + str(d.port),
                "imgs_series": d.imgs_series, "imgs_study": d.imgs_study} 
               for d in devices if d.name!="local"]

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
        return jsonify({"msg":"El dispositivo no existe"}, status = 500)
    except Exception as e:
        return jsonify({"msg":"Error al leer la base de datos"}, status = 500)      

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
    missing_series = application.check_storage_manager.find_missing_series(request.json['device'], studydate)

    # Extract missing series data from datasets
    series_data = []
    for ds in missing_series:
        ds_data = read_dataset(ds, ['PatientName','PatientID',
                                    'StudyDescription','StudyInstanceUID','StudyDate','StudyTime',
                                    'SeriesTime','SeriesNumber','Modality','SeriesDescription',device['imgs_series'],'SeriesInstanceUID'],
                                    field_names = {device['imgs_series']:'ImgsSeries'}, 
                                    default_value = '',
                                    fields_handlers = {'PatientName': lambda x: str(x.value)})
        ds_data['source'] = request.json['device']
        ds_data['level'] = 'SERIES'
        series_data.append(ds_data)        
        
    data = {
        "data": series_data
    }
    
    return data

@application.route('/check_storage_progress')
def check_storage_progress():

    return {"data": {
        "status": application.check_storage_manager.status,
        "progress": f"{100*application.check_storage_manager.progress:.0f}%"
    }}

@application.route('/empty_table', methods = ['GET','POST'])
def empty_table():
    
    return {"data": ""}

@application.route('/tasks')
def tasks():
    return render_template('tasks.html')

@application.route('/get_tasks_table')
def get_tasks_table():

    data = application.task_manager.get_tasks_table()

    return {"data": data}

@application.route('/move', methods=['GET', 'POST'])
def move():    
    
    
    # Get source and destination ae_title from database
    try:
        device = Device.query.get(request.json['destination'])
        assert device
    except AssertionError:
        return jsonify({"msg":"El dispositivo no existe"}, status = 500)
    except Exception as e:
        return jsonify({"msg":"Error al leer la base de datos"}, status = 500)      
    destination = device.ae_title 

    # Get items to send and remove repeated ones
    datasets = request.json['items']
    studies_uids = [ds['StudyInstanceUID'] for ds in datasets if ds['level'] == 'STUDY']
    datasets = list(filter(lambda x: not (x['level'] == 'SERIES' and x['StudyInstanceUID'] in studies_uids), datasets))
        
    # Send datasets
    for task_data in datasets:
        task_data['destination'] = destination
        task_data['type'] = 'MOVE'
        application.task_manager.manage_task(action = 'new', task_data = task_data)

    return {"message": f"Se agregaron {len(datasets)} trabajos a la cola"}
    
@application.route('/task_action', methods=['GET', 'POST'])
def task_action():
    
    ids = request.json['ids']
    for task_id in ids:
        application.task_manager.manage_task(action = request.json['action'], task_id = task_id)
    return {"data": "success"}

@application.route('/manage_devices', methods=['GET', 'POST'])
def manage_devices():
    
    device_name = request.json["name"]
    ae_title = request.json["ae_title"]

    # Query database for device
    d = Device.query.get(device_name)
       
    action = request.json["action"]
    if action == "delete":
        if not d: return {"message":"Error: el dispositivo no existe"}  
        # Delete device and associated filters     
        try:   
            db.session.delete(d)
            for f in d.filters.all():
                db.session.delete(f)  
            db.session.commit()
            return {"message":"Dispositivo eliminado correctamente"}
        except:
            return {"message":"Error al acceder a la base de datos"}
    
    
    # Check if IP is formatted correctly
    address = request.json["address"]
    try:
        ipaddress.ip_address(address)
    except ValueError:
        return {"message":"Error: la dirección IP no es válida"}    
    
    # Check port
    port = request.json["port"]
    try:
        assert port.isnumeric()
        port = int(port)
    except:
        return {"message":"Error: el puerto no es válido"}    
            
    if action == "add":
        # Add new device        
        if d: return {"message":"Error: el dispositivo ya existe"}    
        try:
            # Add device to database
            new_d = Device(name = device_name, ae_title = ae_title, address = address, port = port,
            imgs_series = request.json["imgs_series"] or "Unknown",
            imgs_study = request.json["imgs_study"] or "Unknown")
            db.session.add(new_d)
            db.session.commit()
            return {"message":"Dispositivo agregado correctamente"}
        except:
            return {"message":"Error al acceder a la base de datos"}
 
    # Edit device
    elif action == "edit":
        # Check if device exists
        if not d: return {"message":"Error: el dispositivo no existe"}   
        
        # Edit device in database     
        try:            
            d.ae_title = ae_title
            d.address = address
            d.port = port
            d.imgs_series = request.json["imgs_series"] or "Unknown"
            d.imgs_study = request.json["imgs_study"] or "Unknown"
            db.session.commit()
        except Exception as e:
            print(repr(e))
            return {"message":"Error al acceder a la base de datos"}

        return {"message":"Dispositivo editado correctamente"}    
    
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

    local = Device.query.get('local')
        
    # Get the IP address for each network interface available
    interfaces = psutil.net_if_addrs()
    stats = psutil.net_if_stats()
    available_networks = {}
    for intface, addr_list in interfaces.items():
        if any(getattr(addr, 'address').startswith("169.254") for addr in addr_list):
            continue
        elif intface in stats and getattr(stats[intface], "isup"):
            available_networks[intface] = addr_list
    ips = []
    [[ips.append(item.address) for item in interface if item.family.name == 'AF_INET' and not item.address == '127.0.0.1'] for interface in available_networks.values()]
    address = '/'.join(ips)
    device = {'ae_title': local.ae_title, 'address': address, 'port': local.port}

    data = {
        "data": device
    }

    return data

@application.route('/manage_local_device', methods=['GET', 'POST'])
def manage_local_device():    
    

    try:
        # Edit device in database
        local = Device.query.get('local')
        local.ae_title = request.json["ae_title"]
    except:
        logger.error('Local device configuration could not be updated on the database')
        return jsonify(message = 'Local device configuration could not be updated on the database'), 500
    
    # Restart DICOM interfaces
    services['store_scp'].restart(request.json["ae_title"]  )
    services['store_scu'].ae_title = request.json["ae_title"]  
            
    return {"message":"Local device was updated successfully"} 