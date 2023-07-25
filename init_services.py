import os, json, logging
from services.store_scp import StoreSCP

# Start logger
logger = logging.getLogger('__main__')

# DICOM Store SCP    
store_scp = StoreSCP()
try:
    with open(os.path.join("config", "local.json"), "r") as jsonfile:         
        config = json.load(jsonfile)
    ae_title = config['ae_title']

# Read configuration file
except Exception as e:
    logger.error("failed when reading local config file. ")
    logger.error(repr(e))
    logger.error("trying to start store scp with default configuration. ")
    try:
        with open(os.path.join("config", "local.json"), "w") as jsonfile:      
            json.dump({'ae_title':'DicomApp'}, 
                       jsonfile, indent = 2)
        ae_title = 'DicomApp'
    except:
        logger.error("failed when writing local config file. ")
        logger.error(repr(e))
        raise IOError
    
# Start service
store_scp.start(ae_title)