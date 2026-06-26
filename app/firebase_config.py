import os
import firebase_admin
from firebase_admin import credentials, firestore, auth, storage
 
# ── Module-level singletons ─────────────────────────────────────────────
# These are set once when init_firebase() is called and reused everywhere
_app  = None
db    = None
bucket= None
 
 
def init_firebase():
    """
    Initialise Firebase Admin SDK.
    Called once from app.py at startup.
    Safe to call multiple times — returns early if already initialised.
    """
    global _app, db, bucket
 
    # Guard: do not initialise twice (e.g. during Flask auto-reload)
    if firebase_admin._apps:
        db     = firestore.client()
        bucket = storage.bucket()
        return
 
    # Load credentials from the JSON key file
    key_path = os.getenv('FIREBASE_CREDENTIALS_PATH', 'secrets/firebase-key.json')
    cred = credentials.Certificate(key_path)
 
    # Initialise the app with project ID and storage bucket
    _app = firebase_admin.initialize_app(cred, {
        'projectId':     os.getenv('FIREBASE_PROJECT_ID'),
        'storageBucket': os.getenv('FIREBASE_STORAGE_BUCKET')
    })
 
    # Create module-level client objects
    db     = firestore.client()
    bucket = storage.bucket()
 
    print('[Firebase] Initialised successfully',
          f'Project: {os.getenv("FIREBASE_PROJECT_ID")}')
