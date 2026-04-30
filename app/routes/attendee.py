from flask import Blueprint, render_template, session, url_for, redirect
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