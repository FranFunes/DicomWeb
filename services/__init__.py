import os
from services.task_manager import TaskManager, CheckStorageManager
from services.dicom_interface import DicomInterface
from services.db_store_handler import store_handler
from app_pkg import application, db
from app_pkg.db_models import Device

# Task Manager
task_manager = TaskManager()
check_storage_manager = CheckStorageManager()
  
# Get SCP AET and port from database or initialize it if not available
with application.app_context():
    try:
        d = Device.query.get('__local_store_SCP__')
        assert d
    except AssertionError:    
        d = Device(name = '__local_store_SCP__',
                ae_title = os.environ.get('DEFAULT_STORE_SCP_AET','DicomWeb'),
                address = '0.0.0.0',
                port = os.environ.get('DEFAULT_STORE_SCP_PORT', 11113),
                imgs_series = "Unknown",
                imgs_study = "Unknown")
        db.session.add(d)
        db.session.commit()

    # Create an Store SCP to receive DICOM objects and store them in the database
    store_scp = DicomInterface(ae_title = d.ae_title, port = d.port)
    store_scp.store_handler = store_handler
    store_scp.start_store_scp()