from flask import (Blueprint, render_template, request,
                        jsonify, session, flash, redirect, url_for)
from app.firebase_config import db
from app.decorators import login_required, role_required
from app.utils.qr_utils import verify_qr_payload
from datetime import datetime, timezone
from google.cloud.firestore import SERVER_TIMESTAMP, Increment
 
checkin_bp = Blueprint('checkin',__name__,url_prefix='/organizer/checkin')
 
 
# ── Helper: perform the actual check-in ──────────────────────────────
def do_checkin(registration_id, event_id, staff_uid):
    """
    Mark a registration as checked in.
    Returns (success: bool, message: str, attendee_name: str)
    """
    reg_ref = db.collection('registrations').document(registration_id)
    reg_doc = reg_ref.get()
 
    if not reg_doc.exists:
        return False, 'Registration not found.', ''
 
    reg = reg_doc.to_dict()
 
    # Verify this registration belongs to the correct event
    if reg.get('event_id') != event_id:
        return False, 'QR code does not match this event.', ''
 
    # Check payment status
    if reg.get('payment_status') != 'paid':
        return False, 'Payment not confirmed for this registration.', ''
 
    # Check if already checked in
    if reg.get('status') == 'checked_in':
        name = reg.get('attendee_name','Attendee')
        return False, f'{name} is already checked in.', name
 
    # Get attendee name for display
    attendee_name = reg.get('attendee_name','Unknown')
 
    # Use Firestore transaction to atomically update registration + event counter
    # Atomically update registration + increment event check-in counter
    reg_ref.update({
        'status':        'checked_in',
        'checked_in_at': SERVER_TIMESTAMP,
        'checked_in_by': staff_uid,
    })

    event_ref = db.collection('events').document(event_id)
    event_ref.update({
        'total_checkins': Increment(1)
    })

    return True, 'Check-in successful!', attendee_name
 
 
# ── SCANNER PAGE ─────────────────────────────────────────────────────
@checkin_bp.route('/<event_id>')
@login_required
@role_required('organizer')
def scanner(event_id):
    event_doc = db.collection('events').document(event_id).get()
    if not event_doc.exists:
        flash('Event not found.','danger')
        return redirect(url_for('events.list_events'))
    event = event_doc.to_dict()
    return render_template('organizer/checkin/scanner.html',
                           event=event, event_id=event_id)
 
 
# ── QR SCAN API — called by JS camera scanner ────────────────────────
@checkin_bp.route('/<event_id>/scan',methods=['POST'])
@login_required
@role_required('organizer')
def scan_qr(event_id):
    """JSON endpoint — called by the camera scanner JS on scan."""
    payload = request.json.get('payload','').strip()
    if not payload:
        return jsonify({'success':False,'message':'Empty QR code.'}),400
 
    registration_id, qr_event_id = verify_qr_payload(payload)
    if not registration_id:
        return jsonify({'success':False,'message':'Invalid or tampered QR code.'}),400
 
    success, message, name = do_checkin(registration_id, event_id, session['uid'])
    return jsonify({'success':success,'message':message,'name':name})
 
 
# ── MANUAL CHECK-IN — search by email or order number ────────────────
@checkin_bp.route('/<event_id>/manual',methods=['POST'])
@login_required
@role_required('organizer')
def manual_checkin(event_id):
    query = request.form.get('query','').strip().lower()
    if not query:
        flash('Please enter an email or order number.','warning')
        return redirect(url_for('checkin.scanner',event_id=event_id))
 
    # Search registrations for this event by email
    docs = (
        db.collection('registrations')
        .where('event_id','==',event_id)
        .where('attendee_email','==',query)
        .limit(1)
        .stream()
    )
    results = list(docs)
 
    if not results:
        flash(f'No registration found for: {query}','warning')
        return redirect(url_for('checkin.scanner',event_id=event_id))
 
    reg_doc = results[0]
    success, message, name = do_checkin(reg_doc.id, event_id, session['uid'])
    category = 'success' if success else 'warning'
    flash(message, category)
    return redirect(url_for('checkin.scanner',event_id=event_id))
 
 
# ── CHECK-IN LOG ─────────────────────────────────────────────────────
@checkin_bp.route('/<event_id>/log')
@login_required
@role_required('organizer')
def checkin_log(event_id):
    docs = (
        db.collection('registrations')
        .where('event_id', '==', event_id)
        .where('status', '==', 'checked_in')
        .stream()
    )
    checkins = sorted(
        [{**d.to_dict(), 'id': d.id} for d in docs],
        key=lambda x: x.get('checked_in_at') or '',
        reverse=True
    )[:50]

    event_doc = db.collection('events').document(event_id).get()
    event = event_doc.to_dict() if event_doc.exists else {}

    return render_template('organizer/checkin/log.html',
                           event=event, event_id=event_id, checkins=checkins)