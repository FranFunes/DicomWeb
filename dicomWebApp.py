from app_pkg import application, db
from app_pkg.db_models import Patient, Study

@application.shell_context_processor
def make_shell_context():
    return {'db': db, 'Patient': Patient, 'Study': Study}