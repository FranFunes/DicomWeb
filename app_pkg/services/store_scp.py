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