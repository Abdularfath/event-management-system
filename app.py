import os
from flask import Flask, jsonify
from dotenv import load_dotenv
from flask_wtf.csrf import CSRFProtect
from app.firebase_config import init_firebase
 
load_dotenv()
 
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-change-this')
csrf = CSRFProtect(app)
 
# Initialise Firebase
init_firebase()
 
# ── Register blueprints ─────────────────────────────────────────────
from app.routes.test import test_bp
from app.routes.auth import auth_bp
from app.routes.public import public_bp
from app.routes.organizer import organizer_bp
from app.routes.attendee import attendee_bp
from app.routes.admin import admin_bp
 
app.register_blueprint(test_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(public_bp)
app.register_blueprint(organizer_bp)
app.register_blueprint(attendee_bp)
app.register_blueprint(admin_bp)
 
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
