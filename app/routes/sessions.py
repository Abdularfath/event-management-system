from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.firebase_config import db
from app.decorators import login_required, role_required
from app.routes.events import get_event_or_403
import uuid

sessions_bp = Blueprint('sessions', __name__, url_prefix='/organizer/events/<event_id>/sessions')

@sessions_bp.route('/')
@login_required
@role_required('organizer')
def list_sessions(event_id):
    """List all sessions for a specific event."""
    doc, event_data = get_event_or_403(event_id)
    if not doc:
        return redirect(url_for('events.list_events'))

    # Fetch sessions from the subcollection
    sessions_ref = db.collection('events').document(event_id).collection('sessions')
    docs = sessions_ref.order_by('start_time').stream()
    
    sessions = [{**d.to_dict(), 'id': d.id} for d in docs]
    
    return render_template('organizer/sessions/list.html', event=event_data, event_id=event_id, sessions=sessions)

@sessions_bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('organizer')
def create_session(event_id):
    """Create a new session."""
    doc, event_data = get_event_or_403(event_id)
    if not doc:
        return redirect(url_for('events.list_events'))

    if request.method == 'POST':
        session_data = {
            'title': request.form.get('title'),
            'description': request.form.get('description'),
            'date': request.form.get('date'),
            'start_time': request.form.get('start_time'),
            'end_time': request.form.get('end_time'),
            'track': request.form.get('track', ''),
            'stream_url': request.form.get('stream_url', '')
        }
        
        db.collection('events').document(event_id).collection('sessions').add(session_data)
        flash('Session created successfully!', 'success')
        return redirect(url_for('sessions.list_sessions', event_id=event_id))

    return render_template('organizer/sessions/form.html', event=event_data, event_id=event_id)

@sessions_bp.route('/<session_id>/delete', methods=['POST'])
@login_required
@role_required('organizer')
def delete_session(event_id, session_id):
    """Delete a session."""
    doc, event_data = get_event_or_403(event_id)
    if doc:
        db.collection('events').document(event_id).collection('sessions').document(session_id).delete()
        flash('Session deleted.', 'info')
    return redirect(url_for('sessions.list_sessions', event_id=event_id))

# ADD THIS AT THE BOTTOM OF app/routes/sessions.py

@sessions_bp.route('/<session_id>/speakers', methods=['GET', 'POST'])
@login_required
@role_required('organizer')
def manage_session_speakers(event_id, session_id):
    """Assign or unassign speakers to a specific session."""
    from flask import session as flask_session  # Avoid naming collision
    doc, event_data = get_event_or_403(event_id)
    if not doc:
        return redirect(url_for('events.list_events'))

    session_ref = db.collection('events').document(event_id).collection('sessions').document(session_id)
    session_doc = session_ref.get()
    
    if not session_doc.exists:
        flash('Session not found.', 'danger')
        return redirect(url_for('sessions.list_sessions', event_id=event_id))

    # Fetch ALL speakers belonging to this organizer
    all_speakers_docs = db.collection('speakers').where('organizer_uid', '==', flask_session.get('uid')).stream()
    all_speakers = [{**d.to_dict(), 'id': d.id} for d in all_speakers_docs]

    if request.method == 'POST':
        # Get list of checked speaker IDs from the form
        selected_speaker_ids = request.form.getlist('speaker_ids')
        
        # 1. Clear existing junction documents (easiest way to resync)
        existing_docs = session_ref.collection('session_speakers').stream()
        for d in existing_docs:
            d.reference.delete()
            
        # 2. Add the newly selected speakers to the subcollection
        for sp_id in selected_speaker_ids:
            session_ref.collection('session_speakers').add({'speaker_id': sp_id})
            
        flash('Speakers assigned successfully!', 'success')
        return redirect(url_for('sessions.list_sessions', event_id=event_id))

    # GET request: Fetch currently assigned speakers to pre-check the boxes
    assigned_docs = session_ref.collection('session_speakers').stream()
    assigned_ids = [d.to_dict().get('speaker_id') for d in assigned_docs]

    return render_template(
        'organizer/sessions/speakers.html', 
        event=event_data, 
        event_id=event_id, 
        session_data={**session_doc.to_dict(), 'id': session_doc.id}, 
        all_speakers=all_speakers, 
        assigned_ids=assigned_ids
    )