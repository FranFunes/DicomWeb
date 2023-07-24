from app_pkg import application
from flask import render_template, request
import json, ipaddress
from app_pkg.aux_funcs import read_dataset, find_imgs_in_field
from datetime import datetime, timedelta
from pydicom.multival import MultiValue
from app_pkg.dicom.dicom_interface import DicomInterface

@application.route('/')
@application.route('/index')
@application.route('/queryRetrieve')
def query_retrieve():    
    return render_template('queryRetrieve.html')

@application.route('/search_studies', methods = ['GET','POST'])
def search_studies():

    # Get device info from configuration
    with open("config/devices.json", "r") as jsonfile:         
        devices = json.load(jsonfile)    
    device = devices[request.json['device']]
    
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
    ae = DicomInterface(ae_title = 'BECARIOSPANCHO')    
    responses = ae.query_studies_in_device(device, qr, rs)
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

@application.route('/get_study_data', methods=['GET', 'POST'])
def get_study_data():
    
    # Get device info from configuration
    with open("config/devices.json", "r") as jsonfile:         
        devices = json.load(jsonfile)    
    device = devices[request.json['source']]    
    
    # Build the data for the dicom query
    rs = {'SeriesNumber':'',
          'SeriesDate': '',
          'SeriesTime': '',
          'SeriesDescription': '',
          'Modality':'',
          device['imgs_series']: ''}
          
    # Send the dicom query
    ae = DicomInterface(ae_title = 'BECARIOSPANCHO')
    responses = ae.query_series_in_study(device, request.json['StudyInstanceUID'], responses = rs)
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

    with open("config/devices.json", "r") as jsonfile:         
        devices = json.load(jsonfile)    

    devices = [{"name":key, "ae_title":value["ae_title"], "address":value["address"] + ":" + str(value["port"]),
                "imgs_series": value["imgs_series"], "imgs_study": value["imgs_study"]} 
               for key,value in devices.items()]

    data = {
        "data": devices
    }

    return data

@application.route('/checkStorage')
def check_storage():    
    return render_template('checkStorage.html')

@application.route('/find_missing_series', methods = ['GET','POST'])
def find_missing_series():

    # Get device info from configuration
    with open("config/devices.json", "r") as jsonfile:         
        devices = json.load(jsonfile)    
    device = devices[request.json['device']]

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
    
    # Get source and destination ae_title
    with open("config/devices.json", "r") as jsonfile:         
        devices = json.load(jsonfile)    
    destination = devices[request.json['destination']]["ae_title"]    

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
    
    with open("config/devices.json", "r") as jsonfile:         
        devices = json.load(jsonfile)    
    
    action = request.json["action"]
    device_name = request.json["name"]

    # Check if device already exists        
    device_exists = device_name in devices
    if action == "delete":
        if not device_exists: return {"message":"Error: el dispositivo no existe"}   

        # Delete device from config file
        del devices[device_name]
        with open("config/devices.json", "w") as jsonfile:         
                json.dump(devices, jsonfile, indent = 2)

        # Delete device from series_filters file
        with open("config/series_filters.json", "r") as jsonfile:         
            series_filters = json.load(jsonfile)  
        del series_filters[device_name]
        with open("config/series_filters.json", "w") as jsonfile:         
                json.dump(series_filters, jsonfile, indent = 2)

        return {"message":"Dispositivo eliminado correctamente"}
    
    # Check if AE title already exists
    ae_title = request.json["ae_title"]

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
    
    
    device = {"ae_title": ae_title, "address": address, "port": port}
    
    # Add new device
    if action == "add":
        
        if device_exists: return {"message":"Error: el dispositivo ya existe"}    

        # Get the DICOM field used by the device to show the number of
        # imgs in each series (important to check storage)
        field_names = {"imgs_series": request.json["imgs_series"] or "Unknown",
                       "imgs_study": request.json["imgs_study"] or "Unknown"}
        
        device.update(field_names)

        # Add device to config file
        devices[device_name] = device
        with open("config/devices.json", "w") as jsonfile:         
                json.dump(devices, jsonfile, indent = 2)     

        # Add device to series_filters file
        with open("config/series_filters.json", "r") as jsonfile:         
            series_filters = json.load(jsonfile)  
        series_filters[device_name] = {}
        with open("config/series_filters.json", "w") as jsonfile:         
                json.dump(series_filters, jsonfile, indent = 2)
        
        return {"message":"Dispositivo agregado correctamente"}

    # Edit device
    elif action == "edit":
        # Check if device exists
        if not device_exists: return {"message":"Error: el dispositivo no existe"}   
        
        # Edit device in config file
        devices[device_name].update(device)
        with open("config/devices.json", "w") as jsonfile:         
                json.dump(devices, jsonfile, indent = 2)

        return {"message":"Dispositivo editado correctamente"}    
    
@application.route('/query_imgs_field', methods=['GET', 'POST'])
def query_imgs_field():
    
    device = request.json
    device["port"] = int(device["port"])
    field_names = find_imgs_in_field(device)
    
    return field_names