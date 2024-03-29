import os, logging
from app_pkg import db
from sqlalchemy import event

logger = logging.getLogger('__main__')

class Patient(db.Model):
    PatientID = db.Column(db.String(64), primary_key=True)
    PatientName = db.Column(db.String(64), index=True)

    # Cross-references down
    studies = db.relationship('Study', backref='patient', lazy='dynamic', cascade='all, delete-orphan')    
    series = db.relationship('Series', backref='patient', lazy='dynamic')    
    instances = db.relationship('Instance', backref='patient', lazy='dynamic')    
    
    def __repr__(self):
        return f'<Patient {self.PatientName}>'
    
class Study(db.Model):

    StudyInstanceUID = db.Column(db.String(64), primary_key=True)
    StudyDate = db.Column(db.DateTime, index=True)    
    StudyDescription = db.Column(db.String(64), index=True)
    path = db.Column(db.String(256), index=True)

    # Cross-references up
    PatientID = db.Column(db.String(64), db.ForeignKey('patient.PatientID'))

    # Cross-references down
    series = db.relationship('Series', backref='study', lazy='dynamic', cascade='all, delete-orphan')    
    instances = db.relationship('Instance', backref='study', lazy='dynamic')     

    def __repr__(self):
        return f'<Study {self.StudyDescription} from {self.PatientID}>'
    
class Series(db.Model):

    SeriesInstanceUID = db.Column(db.String(64), primary_key=True)
    SeriesDate = db.Column(db.DateTime, index=True)
    SeriesDescription = db.Column(db.String(64), index=True)
    SeriesNumber = db.Column(db.Integer())
    Modality = db.Column(db.String(64), index=True)
    path = db.Column(db.String(256), index=True)

    # Cross-references up
    PatientID = db.Column(db.String(64), db.ForeignKey('patient.PatientID'))
    StudyInstanceUID = db.Column(db.String(64), db.ForeignKey('study.StudyInstanceUID'))

    # Cross-references down
    instances = db.relationship('Instance', backref='series', lazy='dynamic', cascade='all, delete-orphan')     

    def __repr__(self):
        return f'<Series {self.SeriesDescription} from {self.PatientID}>'    
    
class Instance(db.Model):

    SOPInstanceUID = db.Column(db.String(64), primary_key=True)
    SOPClassUID = db.Column(db.String(64), index=True)   
    filename = db.Column(db.String(256), index=True)

    # Cross-references up
    PatientID = db.Column(db.String(64), db.ForeignKey('patient.PatientID'))
    StudyInstanceUID = db.Column(db.String(64), db.ForeignKey('study.StudyInstanceUID'))
    SeriesInstanceUID = db.Column(db.String(64), db.ForeignKey('series.SeriesInstanceUID'))     

    def __repr__(self):
        return f'<Instance {self.SOPClassUID} from {self.PatientID} stored at {self.filename}>'
    
@event.listens_for(Instance, 'before_delete')
def delete_instance(mapper, connection, target):
    # Delete file from disk
    try:
        os.remove(target.filename)
    except:
        logger.error(f"could'n delete {target.filename} from storage")
    
class Device(db.Model):

    name = db.Column(db.String(64), primary_key=True)
    ae_title = db.Column(db.String(64), index=True)
    address = db.Column(db.String(16), index=True)
    port = db.Column(db.Integer(), index=True)
    imgs_series = db.Column(db.String(64))
    imgs_study = db.Column(db.String(64))

    # Cross-references down
    basic_filters = db.relationship('BasicFilter', backref='device', lazy='dynamic')  

    def __repr__(self):
        return f'<Device {self.name}: {self.ae_title}@{self.address}>'

class BasicFilter(db.Model):

    id = db.Column(db.Integer(), primary_key=True)
    field = db.Column(db.String(64), index=True)
    value = db.Column(db.String(64), index=True)

    # Cross-references up
    device_name = db.Column(db.String(64), db.ForeignKey('device.name'))

    def __repr__(self):
        return f'<Basic filter {self.field}: {self.value} for device {self.device_name}>'
    


