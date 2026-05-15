

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.firebase_config import db
from app.decorators import login_required, role_required
from datetime import datetime, timezone

# 1. Define the Blueprint (This was missing!)
attendee_bp = Blueprint('attendee', __name__, url_prefix='/attendee')

# 2. The Route
@attendee_bp.route('/my-events')
@login_required
@role_required('attendee')
def my_events():
    """Displays all tickets/events the attendee has registered for."""
    uid = session.get('uid')
    
    # Fetch all registrations for this user
        # Change it to attendee_uid!
    regs_ref = db.collection('registrations').where('attendee_uid', '==', uid).stream()
    registrations = []
    
    for r in regs_ref:
        reg_data = r.to_dict()
        reg_data['id'] = r.id
        
        # Fetch the associated event details so we can show the Event Name/Date
        event_doc = db.collection('events').document(reg_data.get('event_id')).get()
        if event_doc.exists:
            reg_data['event'] = event_doc.to_dict()
        else:
            reg_data['event'] = {'name': 'Event Ended/Deleted', 'start_datetime': None}
            
        registrations.append(reg_data)
        
    # Sort them newest first
    fallback_date = datetime(1970, 1, 1, tzinfo=timezone.utc)
    registrations.sort(key=lambda x: x.get('created_at') or fallback_date, reverse=True)

    return render_template('attendee/my_events.html', registrations=registrations)
@attendee_bp.route('/save_session/<event_id>/<session_id>', methods=['POST'])
@login_required
@role_required('attendee')
def save_session(event_id, session_id):
    """Toggles saving a session to the attendee's personal itinerary."""
    uid = session.get('uid')
    doc_ref = db.collection('attendees').document(uid).collection('saved_sessions').document(session_id)
    
    # Toggle logic: If it exists, delete it (unsave). If it doesn't, create it (save).
    if doc_ref.get().exists:
        doc_ref.delete()
        flash('Session removed from your itinerary.', 'info')
    else:
        doc_ref.set({'event_id': event_id})
        flash('Session saved to your itinerary!', 'success')
        
    # Redirect back to the public event details page
    # IMPORTANT: Change 'public.event_details' if your route is named differently!
    return redirect(url_for('public.event_detail', event_id=event_id))

from google.cloud.firestore import SERVER_TIMESTAMP

@attendee_bp.route('/<event_id>/<ticket_type_id>/waitlist', methods=['POST'])
@login_required
@role_required('attendee')
def join_waitlist(event_id, ticket_type_id):
    uid = session.get('uid')
    email = session.get('email')

    # Check if they are already on the waitlist
    existing = db.collection('events').document(event_id).collection('waitlist') \
                 .where('attendee_uid', '==', uid) \
                 .where('ticket_type_id', '==', ticket_type_id) \
                 .limit(1).stream()
    
    if len(list(existing)) > 0:
        flash('You are already on the waitlist for this ticket!', 'info')
        return redirect(url_for('public.event_detail', event_id=event_id))

    # Add to waitlist
    db.collection('events').document(event_id).collection('waitlist').add({
        'attendee_uid': uid,
        'attendee_email': email,
        'ticket_type_id': ticket_type_id,
        'status': 'waiting',
        'joined_at': SERVER_TIMESTAMP
    })

    flash('You have been added to the waitlist! We will email you if a spot opens up.', 'success')
    return redirect(url_for('public.event_detail', event_id=event_id))