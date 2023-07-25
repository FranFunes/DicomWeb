from pynetdicom import AE, evt
from pynetdicom.sop_class import PositronEmissionTomographyImageStorage, Verification
from pydicom.dataset import Dataset
import pydicom
import logging, os, json
from datetime import datetime

# Setup logging behaviour
logger = logging.getLogger('__main__')

pydicom.config.convert_wrong_length_to_UN = True


class StoreSCP(AE):    

    """ 
        The main class for creating and managing DICOM Store Service Class Provider.
        Inherits from pynetdicom AE class, so it has similar functionality.
        Some properties and methods are added to simplify its usage as a DICOM Store SCP:
    
        Properties:
            · scp_queue: received datasets are put into this queue. Another process is responsable
              for consuming this queue.            
                       
        Methods:
            · start: starts the server.
            · stop: stops the server (after all current transfers and existing associations are cleared up).
    
    """

    def __init__(self, scp_queue, store_dest = 'incoming', ae_title = 'ClientAI', address = '0.0.0.0', port = 11115, *args, **kwargs):

        super().__init__(ae_title, *args,**kwargs)

        # Set class properties
        self.queue = scp_queue
        self.store_dest =  store_dest
        
        # Add supported contexts
        self.add_supported_context(PositronEmissionTomographyImageStorage)
        self.add_supported_context(Verification)

        # Create store directory if it does not exist.
        try:
            os.makedirs(store_dest, exist_ok = True)
            logger.debug('Destination directory created successfully')
        except:
            logger.error('Destination directory could not be created')

        # Implement a handler for evt.EVT_C_STORE
        def handle_store(event):

            """Handle a C-STORE request event."""
            
            # Decode dataset and extract meta information
            ds = event.dataset
            ds.file_meta = event.file_meta

            # Construct an unique fname for each dataset received
            timestamp = datetime.now()
            fname = os.path.join(self.store_dest, timestamp.strftime('%Y%m%d%H%m%S%f'))
            
            # Create a new dataset to pass relevant fields to further processing
            new_ds = Dataset()
            recon_ds = Dataset()            

            # Append information to the recon_ds
            fields = ['PixelSpacing', 
                      'ReconstructionMethod',
                      'Manufacturer',
                      'ManufacturerModelName',
                      'SliceThickness',
                      'ConvolutionKernel',
                      'PatientWeight',
                      'ActualFrameDuration',
                      'RadiopharmaceuticalInformationSequence',
                      0x000910B3,
                      0x000910B2,
                      0x000910BA,
                      0x000910BB,
                      0x000910DC]
            for field in fields:
                try:
                    recon_ds[field] = ds[field]
                except:
                    logger.debug(f"{field} not available")

            try:
                # Write dataset to disk
                ds.save_as(fname, write_like_original = False)
                logger.debug("New dataset written to disk successfully")

                # Append mandatory information to the new dataset
                new_ds.StudyInstanceUID = ds.StudyInstanceUID
                new_ds.SeriesInstanceUID = ds.SeriesInstanceUID
                new_ds.SOPInstanceUID = ds.SOPInstanceUID
                new_ds.ImagePositionPatient = ds.ImagePositionPatient
                # Append non mandatory information
                fields = ['NumberOfSlices','PatientName','StudyDate','SeriesDescription']
                for field in fields:
                    try:
                        new_ds[field] = ds[field]
                    except:
                        logger.info(f"{field} not available")  
                        
                # Put relevant information in processing queue
                element = {'filename':fname, 'dataset':new_ds, 'recon_ds':recon_ds,
                           'address': event.assoc.requestor.info['address'],
                           'ae_title': event.assoc.requestor.info['ae_title']}
                    
                self.queue.put(element)

                # Return a 'Success' status
                return 0x0000 

            except AttributeError:
                logger.debug("New dataset could not be processed. Missing DICOM information?")

                # Return error code and log failure information
                return 0xA700  
            
            except FileNotFoundError as e:
                logger.debug("New dataset could not be saved - No such file or directory")
                logger.debug(repr(e))

                # Return error code and log failure information
                return 0xA700  
            
            except Exception as e:
                logger.debug("New dataset could not be saved - unknown error")
                logger.debug(repr(e))

                # Return error code and log failure information
                return 0xA700  
        
        # Implement a handler for evt.EVT_C_ECHO
        def handle_echo(event):
            """Handle a C-ECHO request event."""
            return 0x0000

        self.handle_store = handle_store
        self.handle_echo = handle_echo

    def start(self, ae_title):        

        """    

        Starts the DICOM Store Service Class Provider.

        """                      
        
        handlers = [(evt.EVT_C_STORE, self.handle_store), (evt.EVT_C_ECHO, self.handle_echo)]   

        # Start listening for incoming association requests
        if not self.get_status() == 'Running':
            try:
                self.server = self.start_server(address = ('0.0.0.0', 11113), ae_title = ae_title, evt_handlers=handlers, block = False)     
                logger.info('Starting Store SCP: ' + ae_title + '@0.0.0.0:11113')
                return "Dicom Listener started successfully"
            except Exception as e:
                logger.error('Failed when starting StoreSCP ' + ae_title + '@0.0.0.0:11113')
                logger.error(repr(e))
                return "Dicom Listener could not be started"
        else:
            return 'Dicom Listener is already running'

    def stop(self):

        """ Stops the SCP """ 
        try:               
            self.server.shutdown()
            logger.info("Store SCP stopped")
            return 'Dicom Listener stopped!'
        except:
            logger.error("Store SCP could not be stopped")
            return 'Dicom Listener could not be stopped!'


    def restart(self, ae_title):
        try:
            self.stop()
        except Exception as e: 
            logger.info("Server could not be stopped")
            logger.info(repr(e))
        self.start(ae_title)

    def get_status(self):

        if not hasattr(self,"server"):
            state = 'Not started'
        else:
            state = 'Stopped'
            # Create an AE and send a C - ECHO to ourselves            
            ae = AE()            
            ae.add_requested_context(Verification)
            assoc = ae.associate("127.0.0.1", 11113)

            if assoc.is_established:
                status = assoc.send_c_echo()
                if status:                                        
                    try:
                        assert status.Status == 0                        
                        state = 'Running'
                    except:
                        pass
                else:
                    logger.error("Connection timed out, was aborted or received invalid response")                    

                # Release the association
                assoc.release()
            else:
                logger.error("Association rejected, aborted or never connected")                                    
        
        return state