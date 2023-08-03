from app_pkg import db

class Patient(db.Model):
    PatientID = db.Column(db.String(64), primary_key=True)
    PatientName = db.Column(db.String(64), index=True)

    # Cross-references down
    studies = db.relationship('Study', backref='patient', lazy='dynamic')    
    series = db.relationship('Series', backref='patient', lazy='dynamic')    
    instances = db.relationship('Instance', backref='patient', lazy='dynamic')    
    
    def __repr__(self):
        return f'<Patient {self.PatientName}>'
    
class Study(db.Model):

    StudyInstanceUID = db.Column(db.String(64), primary_key=True)
    StudyDate = db.Column(db.DateTime, index=True)    
    StudyDescription = db.Column(db.String(64), index=True)

    # Cross-references up
    PatientID = db.Column(db.String(64), db.ForeignKey('patient.PatientID'))

    # Cross-references down
    series = db.relationship('Series', backref='study', lazy='dynamic')    
    instances = db.relationship('Instance', backref='study', lazy='dynamic')     

    def __repr__(self):
        return f'<Study {self.StudyDescription} from {self.PatientID}>'
    
class Series(db.Model):

    SeriesInstanceUID = db.Column(db.String(64), primary_key=True)
    SeriesDate = db.Column(db.DateTime, index=True)
    SeriesDescription = db.Column(db.String(64), index=True)
    SeriesNumber = db.Column(db.Integer())
    Modality = db.Column(db.String(64), index=True)

    # Cross-references up
    PatientID = db.Column(db.String(64), db.ForeignKey('patient.PatientID'))
    StudyInstanceUID = db.Column(db.String(64), db.ForeignKey('study.StudyInstanceUID'))

    # Cross-references down
    instances = db.relationship('Instance', backref='series', lazy='dynamic')     

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
    
class Device(db.Model):

    name = db.Column(db.String(64), primary_key=True)
    ae_title = db.Column(db.String(64), index=True)
    address = db.Column(db.String(16), index=True)
    port = db.Column(db.Integer(), index=True)
    imgs_series = db.Column(db.String(64))
    imgs_study = db.Column(db.String(64))

    # Cross-references down
    filters = db.relationship('Filter', backref='device', lazy='dynamic')  

    def __repr__(self):
        return f'<Device {self.name}: {self.ae_title}@{self.address}>'

class Filter(db.Model):

    id = db.Column(db.Integer(), primary_key=True)
    field = db.Column(db.String(64), index=True)
    value = db.Column(db.String(64), index=True)

    # Cross-references up
    device_name = db.Column(db.String(64), db.ForeignKey('device.name'))

    def __repr__(self):
        return f'<Filter {self.field}: {self.value} for device {self.device_name}>'
    


