import os
os.environ['NO_PROXY'] = 'localhost,127.0.0.1,11434'

from flask import Flask
from app.config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv
from flask_moment import Moment

load_dotenv()
app = Flask(__name__, static_folder='../static')
moment = Moment(app)

app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db)

from app import routes, models