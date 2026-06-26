from flask import Blueprint, render_template, request, jsonify, session
from app.firebase_config import db
from google.cloud.firestore import Increment, transactional
from app.decorators import login_required, role_required
from app.utils.qr_utils import verify_qr_payload

checkin_bp = Blueprint('checkin', __name__, url_prefix='/organizer/events/<event_id>/checkin')

@checkin_bp.route('/scanner', methods=['GET'])
@login_required
@role_required('organizer')
def scanner(event_id):
    """Renders the QR Code scanner interface using HTML5-QRCode."""
    # Verify the organizer owns this event
    event_doc = db.collection('events').document(event_id).get()
    if not event_doc.exists or event_doc.to_dict().get('organizer_uid') != session.get('uid'):
        return "Event not found or unauthorized", 403
    
    return render_template('organizer/checkin/scanner.html', event_id=event_id, event=event_doc.to_dict())

@checkin_bp.route('/verify', methods=['POST'])
@login_required
@role_required('organizer')
def verify_scan(event_id):
    """API endpoint that receives the scanned QR payload and updates Firestore."""
    print(f"[DEBUG CHECKIN] Request received for event: {event_id}", flush=True)
    
    try:
        data = request.get_json()
        payload = data.get('qr_payload')
        print(f"[DEBUG CHECKIN] Payload: {payload}", flush=True)
    except Exception as e:
        print(f"[DEBUG CHECKIN] Failed to parse JSON: {e}", flush=True)
        return jsonify({'success': False, 'message': 'Invalid JSON request.'}), 400

    if not payload:
        print("[DEBUG CHECKIN] Error: No payload provided.", flush=True)
        return jsonify({'success': False, 'message': 'No QR code payload provided.'}), 400

    # 1. Verify HMAC signature
    is_valid, reg_id, payload_event_id = verify_qr_payload(payload)
    print(f"[DEBUG CHECKIN] Validation Result -> Valid: {is_valid}, RegID: {reg_id}", flush=True)

    if not is_valid:
        return jsonify({'success': False, 'message': '❌ Invalid or forged QR Code!'}), 400
    
    if payload_event_id != event_id:
        return jsonify({'success': False, 'message': '❌ Ticket belongs to a different event!'}), 400

    # 2. Database transaction variables
    transaction_obj = db.transaction()
    reg_ref = db.collection('registrations').document(reg_id)
    event_ref = db.collection('events').document(event_id)

    @transactional  
    def process_checkin(transaction_obj, reg_ref, event_ref):
        reg_doc = reg_ref.get(transaction=transaction_obj)
        
        if not reg_doc.exists:
            return {'success': False, 'message': '❌ Registration not found.', 'code': 404}

        reg_data = reg_doc.to_dict()

        if reg_data.get('status') == 'checked_in':
            return {'success': False, 'message': f'⚠️ Already checked in! ({reg_data.get("attendee_name")})', 'code': 400}
        
        if reg_data.get('status') != 'confirmed':
            return {'success': False, 'message': '❌ Ticket is cancelled or payment is pending.', 'code': 400}

        # 3. Mark as Checked In
        transaction_obj.update(reg_ref, {'status': 'checked_in'})

        # 4. Increment Event Check-In Counter
        transaction_obj.update(event_ref, {'total_checkins': Increment(1)})

        return {
            'success': True, 
            'message': '✅ Check-in successful!',
            'attendee_name': reg_data.get("attendee_name"),
            'ticket_type': reg_data.get("ticket_type_name"),
            'code': 200
        }

    # Execute the transaction
    result = process_checkin(transaction_obj, reg_ref, event_ref)
    
    return jsonify(result), 200