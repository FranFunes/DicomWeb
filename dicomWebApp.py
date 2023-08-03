import os, logging
from datetime import datetime
from pynetdicom.events import Event
from pydicom.dataset import Dataset
from app_pkg import application, db
from app_pkg.db_models import Patient, Study, Series, Instance, Device, Filter
from app_pkg.dicom_interface import DicomInterface

logger = logging.getLogger('__main__')

@application.shell_context_processor
def make_shell_context():
    return {'db': db, 'Patient': Patient, 'Study': Study, 'Series':Series, 'Instance':Instance,
            'Device': Device, 'Filter': Filter}

# Some functions to manage database operations
def db_create_patient(ds: Dataset) -> Patient:
    
    pat_id = str(ds.PatientID)
    pat_name = str(ds.PatientName)
    with application.app_context():
        # Raise error if patient already exists
        patient = Patient.query.get(pat_id)
        if patient is not None:
            raise ValueError("This patient already exists")
        patient = Patient(PatientID = pat_id, PatientName = pat_name)
        db.session.add(patient)
        db.session.commit()
    return patient

def db_create_study(ds: Dataset) -> Study:

    uid = ds.StudyInstanceUID
    date = datetime.strptime(ds.StudyDate + ds.StudyTime[:6], '%Y%m%d%H%M%S')
    description = ds.StudyDescription
    with application.app_context():
        # Raise error if study already exists
        study = Study.query.get(uid)
        if study is not None:
            raise ValueError("This study already exists")
        # Check if patient already exists and create it if not
        patient = Patient.query.get(ds.PatientID) or db_create_patient(ds)
        study = Study(StudyInstanceUID = uid, 
                      StudyDate = date,
                      StudyDescription = description, 
                      patient = patient)
        db.session.add(study)
        db.session.commit()

    return study
    
def db_create_series(ds: Dataset) -> Series:

    uid = ds.SeriesInstanceUID
    date = datetime.strptime(ds.SeriesDate + ds.SeriesTime[:6], '%Y%m%d%H%M%S')
    description = ds.SeriesDescription
    mod = ds.Modality
    number = ds.SeriesNumber
    with application.app_context():
        # Raise error if series already exists
        series = Series.query.get(uid)
        if series is not None:
            raise ValueError("This series already exists")
        # Check if patient and study already exist or create them if not
        patient = Patient.query.get(ds.PatientID) or db_create_patient(ds)
        study = Study.query.get(ds.StudyInstanceUID) or db_create_study(ds)
        series = Series(SeriesInstanceUID = uid, 
                        SeriesDate = date,
                        SeriesDescription = description, 
                        SeriesNumber = number,
                        Modality = mod, 
                        patient = patient,
                        study = study)
        db.session.add(series)
        db.session.commit()
        
    return series

def db_create_instance(ds: Dataset, filename: str) -> Instance:

    uid = ds.SOPInstanceUID
    uid_class = ds.SOPClassUID
    with application.app_context():
        # Raise error if instance already exists
        instance = Instance.query.get(uid)
        if instance is not None:
            raise ValueError("This instance already exists")
        # Check if patient, study and series already exist or create them if not
        patient = Patient.query.get(ds.PatientID) or db_create_patient(ds)
        study = Study.query.get(ds.StudyInstanceUID) or db_create_study(ds)
        series = Series.query.get(ds.SeriesInstanceUID) or db_create_series(ds)
        instance = Instance(SOPInstanceUID = uid, 
                            SOPClassUID = uid_class,
                            filename = filename,
                            patient = patient,
                            study = study,
                            series = series)
        db.session.add(instance)
        db.session.commit()
        
    return instance

# Create an Store SCP to receive DICOM objects and store them in the database
ae = DicomInterface(ae_title = os.environ['STORE_SCP_AET'], port = int(os.environ['STORE_SCP_PORT']))

# Create a handler for the store request event
def store_handler(event: Event, root_dir = 'incoming') -> int:
    
    try:
        ds = event.dataset
        ds.file_meta = event.file_meta    
        filedir = os.path.join(root_dir, ds.StudyInstanceUID, ds.SeriesInstanceUID)
        os.makedirs(filedir, exist_ok = True)
        filepath = os.path.join(filedir, ds.SOPInstanceUID)
        ds.save_as(filepath, write_like_original = False)
        # Store in the database
        try:
            db_create_instance(ds, filepath)
        except ValueError:
            logger.error("Can't write instance to database: instance already exists")
            return 0x0117

    except Exception as e:
        logger.error(f"Can't write instance to storage: {repr(e)}")
        return 0xA700

    else:
        # Return a 'Success' status
        return 0x0000
        
# Start store SCP
ae.store_handler = store_handler
ae.start_store_scp()
