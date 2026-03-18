import os
from flask import Flask, jsonify
from dotenv import load_dotenv
from app.firebase_config import init_firebase
 
load_dotenv()
 
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret')
 
# Initialise Firebase when the app starts
init_firebase()
 
# ── Routes ─────────────────────────────────────────────────────────────
from app.routes.test import test_bp
app.register_blueprint(test_bp)
 
@app.route('/')
def index():
    return jsonify({
        'message': 'EMS running. Visit /test-firebase to verify DB.',
        'status':  'ok',
        'day':     2
    })
 
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
