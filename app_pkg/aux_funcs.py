import subprocess, os
from shutil import make_archive, copytree, rmtree
from typing import List
from datetime import datetime, timedelta
from pydicom.dataset import Dataset
from pynetdicom.sop_class import StudyRootQueryRetrieveInformationModelFind

from app_pkg import application
from app_pkg.db_models import Device
from services.dicom_interface import DicomInterface

def read_dataset(ds:Dataset, fields_to_read:List[str], field_names:dict = {},
                 default_values = {}, fallback_value = None,
                 fields_handlers:dict = {}, format_datetimes = True):
    """
    
    Extract fields from a Dataset. Args:
    · ds: pydicom.Dataset where the data is to be extracted from
    · fields_to_read: a list of strings with standard dicom field names to extract
    · field_names(opt): a dict with a mapping from a standard dicom field name to a custom name to use in the output dictionary.
    · default_value: a mapping with values to assign when field is not in dataset
    · fallback_value: a value to assign to fields not present in the dataset and not in the default_values mapping.
    · fields_handlers (opt): a dict with a field names as keys and function handlers as elements, to allow custom control of
    how each field is read. By default, the value extracted is ds[fieldname].value
    · format_datetimes (opt): if True (default), date and time fields will be parsed to the dd/mm/yyyy and hh:mm:ss format. (This
    is overriden if a date/time field is in)


    """

    output = {}
    for idx, field in enumerate(fields_to_read):
        try:
            if field in fields_handlers:
                value = fields_handlers[field](ds[field])
            else:
                value = ds[field].value
                if format_datetimes:
                    if ds[field].VR == 'DA':
                        try:
                            value = datetime.strptime(value, '%Y%m%d').strftime('%d/%m/%Y')
                        except:
                            pass
                    elif ds[field].VR == 'TM':
                        try:
                            value = datetime.strptime(value, '%H%M%S').strftime('%H:%M:%S')
                        except:
                            try:
                                value = datetime.strptime(value, '%H%M%S.%f').strftime('%H:%M:%S')
                            except:
                                pass

        except:
            if field in default_values:
                value = default_values[field]
            else:
                value = fallback_value

        if field in field_names:
            name = field_names[field]
        else:
            name = field
        output[name] = value

    return output

def find_imgs_in_field(device: dict) -> dict:

    """    

        Queries a peer AE and tries to find which field is used to inform the number of instances
        in each study and each series
        There are some possible fields where this information could be present:
            · NumberOfStudyRelatedInstances (for study)
            · NumberOfSeriesRelatedInstances (for series) 
            · ImagesInAcquisition (for series)

        Args: device: a dictionary with at least following keys:
                        ae_title: string with the AE title of the peer device.
                        address: string with the IP of the peer device.
                        port: int with the TCP port of the peer device.

        Returns: a dict with the following keys
            "imgs_series": the field where the device inform the number of instances in a series ("Unknown" if not found)
            "imgs_study": the field where the device inform the number of instances in a study ("Unknown" if not found)
                
    """

    # Query the device by date backwards, until at least one study is found, the C-FIND returns fail or
    # the association fails

    ds = Dataset()
    ds.QueryRetrieveLevel = 'STUDY'    
    ds.StudyInstanceUID = ''
    ds.NumberOfStudyRelatedInstances = ''
    
    try:
        with application.app_context():
            ae = DicomInterface(ae_title = Device.query.get('__local_store_SCP__').ae_title)
        assoc = ae.get_association(device)
    except:
        return {"imgs_study": 'Unknown', "imgs_series": 'Unknown'}

    studies_found = False
    c_find_successful = True
    studydate = datetime.today()

    while not studies_found and assoc.is_established and c_find_successful:
        
        # Query device
        ds.StudyDate = studydate.strftime('%Y%m%d')
        c_find_results = assoc.send_c_find(ds, StudyRootQueryRetrieveInformationModelFind)
        query_results = list(c_find_results)
        
        # Check if c_find was succesful
        if query_results[-1][0]:
            c_find_successful = query_results[-1][0].Status == 0
        else:
            c_find_successful = False       

        # Check if any studies were found
        studies_found = len(query_results) > 1

        # Come back yesterday
        studydate = studydate - timedelta(days=1)   
    
    if not c_find_successful:
        imgs_in_series = 'Unknown'
        imgs_in_study = 'Unknown'
    elif not assoc.is_established:
        imgs_in_series = 'Unknown'
        imgs_in_study = 'Unknown'
    else:
        # If at least one study was found, query series for it and try to find the
        # field with the number of images in each series.
        if 'NumberOfStudyRelatedInstances' in query_results[0][1]:
            imgs_in_study = 'NumberOfStudyRelatedInstances'
        else:
            imgs_in_study = 'Unknown'

        ds = Dataset()    
        ds.QueryRetrieveLevel = 'SERIES'
        ds.StudyInstanceUID = query_results[0][1].StudyInstanceUID
        ds.SeriesInstanceUID = ''
        ds.NumberOfSeriesRelatedInstances = ''
        ds.ImagesInAcquisition = ''

        c_find_results = assoc.send_c_find(ds, StudyRootQueryRetrieveInformationModelFind)
        query_results = list(c_find_results)
        
        if 'NumberOfSeriesRelatedInstances' in query_results[0][1]:
            imgs_in_series = 'NumberOfSeriesRelatedInstances'            
        elif 'ImagesInAcquisition' in query_results[0][1]:
            imgs_in_series = 'ImagesInAcquisition'
        else:
            imgs_in_series = 'Unknown'        

    # Release association in case it is still active
    assoc.release()

    return {"imgs_study": imgs_in_study, "imgs_series": imgs_in_series}


def ping(target_host, timeout = 100, count = 3):

    if os.name == "nt":
        command = ["ping", "-w", str(timeout), "-n", str(count), target_host]
    elif os.name == "posix":
        command = ["ping", "-W", str(timeout), "-c", str(count), target_host]
    else:
        return False

    try:
        completed_process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout = completed_process.stdout
        stderr = completed_process.stderr

        if completed_process.returncode == 0:
            return True
        else:
            return False
    except subprocess.CalledProcessError as e:
        return False
    

def zip_files(items: List[dict]) -> str:
    
    os.makedirs('dicomtemp', exist_ok = True)
    for item in items:
        copytree(item.path, 'dicomtemp')
    """
    zip_fname = task.id + '_' + config.client_id
    archive_name = os.path.join(config.zip_dir, zip_fname)        
    make_archive('dicoms', 'zip', 'dicomtemp')

    make_archive()

    """

    
    return os.path.join('dicomtemp','dicom.zip')
