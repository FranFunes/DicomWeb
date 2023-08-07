import logging, os
from logging.handlers import RotatingFileHandler

os.makedirs('logs', exist_ok = True)

class CapitalizeFormatter(logging.Formatter):
    def format(self, record):

        # Put the first character in uppercase
        msg =  record.msg
        msg = msg[0].upper() + msg[1:]
        msg = msg.replace('\n',' ')
        msg = msg.replace(';','-')
        record.msg = msg

        # Remove ; and carriage returns
        return super().format(record)

def dicom_logger():

    logger = logging.getLogger('pynetdicom')
    logger.setLevel(logging.DEBUG)
    logger.handlers = []
    handler = RotatingFileHandler(os.path.join('logs','dicom_events.log'), maxBytes = 10*2**20, backupCount = 10)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s: %(levelname).1s: %(threadName)s: %(message)s ')    
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    handler = RotatingFileHandler(os.path.join('logs','dicom_errors.log'), maxBytes = 10*2**20, backupCount = 1)
    handler.setLevel(logging.ERROR)
    formatter = logging.Formatter('%(asctime)s: %(levelname).1s: %(threadName)s: %(message)s ')    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
   

def app_logger():

    # Configure logging for the application
    app_logger = logging.getLogger('__main__')
    app_logger.handlers = []
    app_logger.setLevel(logging.DEBUG)
    handler = RotatingFileHandler(os.environ['LOGGING_FILE'], maxBytes = 10*2**20, backupCount = 100)
    handler.setLevel(logging.DEBUG)
    formatter = CapitalizeFormatter('%(asctime)s;%(levelname)s;%(module)s;%(funcName)s;%(message)s')
    handler.setFormatter(formatter)
    app_logger.addHandler(handler)
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    formatter = CapitalizeFormatter('%(asctime)s - %(levelname)s in %(module)s @ %(funcName)s: %(message)s')
    handler.setFormatter(formatter)
    app_logger.addHandler(handler)
