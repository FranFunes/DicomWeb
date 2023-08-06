from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config

application = Flask(__name__)
application.config.from_object(Config)

db = SQLAlchemy(application)
migrate = Migrate(application, db)

from app_pkg import routes