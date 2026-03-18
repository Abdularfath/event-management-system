import os
from flask import Flask, jsonify
from dotenv import load_dotenv
 
# Load environment variables from .env file
load_dotenv()
 
# Create the Flask application instance
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret')
 
# ── Health check route ─────────────────────────────────────────────────
@app.route('/')
def index():
    return jsonify({
        'message': 'Hello from EMS! Docker is working.',
        'status':  'ok',
        'project': 'event-management-system',
        'day':     1,
        'sprint':  'Sprint 1 — Foundation'
    })
 
# ── Entry point ────────────────────────────────────────────────────────
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
