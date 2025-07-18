import os, logging, sys
from sqlalchemy.exc import OperationalError
from services.task_manager import TaskManager, CheckStorageManager
from services.dicom_interface import DicomInterface
from services.db_store_handler import store_handler
from services.loggers import app_logger, dicom_logger
from app_pkg import application, db
from app_pkg.db_models import Device

# Configure logging
app_logger()
dicom_logger()
logger = logging.getLogger('__main__')

# Task Manager
task_manager = TaskManager()
check_storage_manager = CheckStorageManager()
  
# Get SCP AET and port from database or initialize it if not available
aet = os.environ.get('DEFAULT_STORE_SCP_AET','DicomWeb')
port = int(os.environ.get('DEFAULT_STORE_SCP_PORT', 11113))
address = os.environ.get('DEFAULT_STORE_SCP_ADDRESS', '0.0.0.0')

with application.app_context():
    try:
        d = Device.query.get('__local_store_SCP__')                
        assert d
        logger.debug('local device found in the database')
        aet = d.ae_title
        port = d.port
        address = d.address

    except AssertionError:        
        logger.info('database is available but local device not found.')
        logger.info('creating local device with default settings.')
        d = Device(name = '__local_store_SCP__',
                ae_title = aet,
                address = address,
                port = port,
                imgs_series = "Unknown",
                imgs_study = "Unknown")
        db.session.add(d)
        db.session.commit()
    except OperationalError:       
        logger.info('database is not available.')
        logger.info('creating local device with default settings.') 
    
    # Create an Store SCP to receive DICOM objects and store them in the database
    store_scp = DicomInterface(ae_title = aet, port = port, address = address)
    store_scp.store_handler = store_handler
    if 'flask' in sys.argv[0] and 'run' in sys.argv:
        logger.info('starting store_scp.') 
        store_scp.start_store_scp()