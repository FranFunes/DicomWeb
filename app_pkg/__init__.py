from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config
from app_pkg.task_manager import TaskManager, CheckStorageManager

application = Flask(__name__)
application.config.from_object(Config)
application.task_manager = TaskManager()
application.check_storage_manager = CheckStorageManager()

db = SQLAlchemy(application)
migrate = Migrate(application, db)

from app_pkg import routes, db_models
