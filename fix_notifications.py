import sys
sys.path.append(" /home/shifthandoversajid/shift_handover_app\)
from flask import Flask
from models.models import db, User
from models.handover_enhanced import HandoverNotification, IncidentAssignment
from config import Config
from datetime import datetime

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)
