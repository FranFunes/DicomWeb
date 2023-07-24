from app_pkg import db

class Patient(db.Model):
    PatientID = db.Column(db.String(64), primary_key=True)
    PatientName = db.Column(db.String(64), index=True)

    # Cross-references down
    studies = db.relationship('Study', backref='patient', lazy='dynamic')    
    series = db.relationship('Series', backref='patient', lazy='dynamic')    
    instances = db.relationship('Instances', backref='patient', lazy='dynamic')    
    
    def __repr__(self):
        return f'<Patient {self.PatientName}>'
    
class Study(db.Model):

    StudyInstanceUID = db.Column(db.String(64), primary_key=True)
    StudyDate = db.Column(db.DateTime, index=True)
    StudyDescription = db.Column(db.String(64), index=True)
    ModalitiesInStudy = db.Column(db.String(64), index=True)

    # Cross-references up
    PatientID = db.Column(db.String(64), db.ForeignKey('patient.PatientID'))

    # Cross-references down
    series = db.relationship('Series', backref='study', lazy='dynamic')    
    instances = db.relationship('Instances', backref='study', lazy='dynamic')     

    def __repr__(self):
        return f'<Study {self.StudyDescription} from {self.PatientID}>'
    
class Series(db.Model):

    SeriesInstanceUID = db.Column(db.String(64), primary_key=True)
    SeriesDate = db.Column(db.DateTime, index=True)
    SeriesDescription = db.Column(db.String(64), index=True)
    Modality = db.Column(db.String(64), index=True)

    # Cross-references up
    PatientID = db.Column(db.String(64), db.ForeignKey('patient.PatientID'))
    StudyInstanceUID = db.Column(db.String(64), db.ForeignKey('study.StudyInstanceUID'))

    # Cross-references down
    instances = db.relationship('Instances', backref='series', lazy='dynamic')     

    def __repr__(self):
        return f'<Series {self.SeriesDescription} from {self.PatientID}>'    
    
class Instance(db.Model):

    SOPInstanceUID = db.Column(db.String(64), primary_key=True)
    SOPClassUID = db.Column(db.String(64), primary_key=True)   
    filename = db.Column(db.String(256), index=True)

    # Cross-references up
    PatientID = db.Column(db.String(64), db.ForeignKey('patient.PatientID'))
    StudyInstanceUID = db.Column(db.String(64), db.ForeignKey('study.StudyInstanceUID'))
    SeriesInstanceUID = db.Column(db.String(64), db.ForeignKey('series.SeriesInstanceUID'))     

    def __repr__(self):
        return f'<Instance {self.SOPClassUID} from {self.PatientID} stored at {self.filename}>'
    
