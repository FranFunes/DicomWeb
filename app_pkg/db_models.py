from app_pkg import db

class Patient(db.Model):
    PatientID = db.Column(db.String(64), primary_key=True)
    PatientName = db.Column(db.String(64), index=True)
    studies = db.relationship('Study', backref='patient', lazy='dynamic')

    def __repr__(self):
        return f'<Patient {self.PatientName}>'
    
class Study(db.Model):
    StudyInstanceUID = db.Column(db.String(64), primary_key=True)
    StudyDate = db.Column(db.DateTime, index=True)
    StudyDescription = db.Column(db.String(64), index=True)
    ModalitiesInStudy = db.Column(db.String(64), index=True)
    PatientID = db.Column(db.String(64), db.ForeignKey('patient.PatientID'))

    def __repr__(self):
        return f'<Study {self.StudyDescription} from {self.PatientID}>'
    
    