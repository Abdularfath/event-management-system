from flask import Blueprint, jsonify
from app.firebase_config import db
from datetime import datetime, timezone
 
test_bp = Blueprint('test', __name__)
 
 
@test_bp.route('/test-firebase')
def test_firebase():
    """
    Smoke test: write a doc to Firestore, read it back, delete it.
    Returns JSON confirming each step worked.
    Remove this route before going to production.
    """
    results = {}
 
    try:
        # ── 1. Write ─────────────────────────────────────────────────
        test_ref = db.collection('_smoke_test').document('day2')
        test_ref.set({
            'project':    'event-management-system',
            'test_day':   2,
            'written_at': datetime.now(timezone.utc).isoformat()
        })
        results['write'] = 'ok'
 
        # ── 2. Read back ─────────────────────────────────────────────
        snap = test_ref.get()
        data = snap.to_dict()
        results['read']  = 'ok' if data else 'empty'
 
        # ── 3. Delete ────────────────────────────────────────────────
        test_ref.delete()
        results['delete'] = 'ok'
 
        return jsonify({
            'status':   'success',
            'message': 'Firebase connected — Firestore read/write working.',
            'results': results
        }), 200
 
    except Exception as e:
        return jsonify({
            'status':  'error',
            'message':str(e)
        }), 500
