from flask import (Blueprint, render_template, redirect,
                        url_for, session, flash, request)
from app.firebase_config import db
from app.decorators import login_required, role_required
from app.utils.validators import validate_event
from datetime import datetime
from google.cloud.firestore import SERVER_TIMESTAMP
import csv
from io import StringIO
from flask import Response
from google.cloud.firestore import Increment
 
events_bp = Blueprint('events', __name__, url_prefix='/organizer/events')
 
FMT = '%Y-%m-%dT%H:%M'  # datetime-local HTML input format
 
 
# ── Helper: get event + verify ownership ─────────────────────────────
def get_event_or_403(event_id):
    doc = db.collection('events').document(event_id).get()
    if not doc.exists:
        return None, None
    data = doc.to_dict()
    if data.get('organizer_uid') != session.get('uid'):
        return None, 'forbidden'
    return doc, data
 
 
# ── Helper: get organizer's venues for dropdown ───────────────────────
def get_my_venues():
    docs = (
        db.collection('venues')
        .where('organizer_uid','==',session['uid'])
        .order_by('name')
        .stream()
    )
    return [{**d.to_dict(),'id':d.id} for d in docs]
 
 
# ── LIST organizer's events ───────────────────────────────────────────
@events_bp.route('/')
@login_required
@role_required('organizer')
def list_events():
    docs = (
        db.collection('events')
        .where('organizer_uid','==',session['uid'])
        .order_by('created_at')
        .stream()
    )
    events = [{**d.to_dict(),'id':d.id} for d in docs]
    return render_template('organizer/events/list.html',events=events)
 
 
# ── CREATE event ──────────────────────────────────────────────────────
@events_bp.route('/create',methods=['GET','POST'])
@login_required
@role_required('organizer')
def create_event():
    venues = get_my_venues()
 
    if request.method == 'POST':
        form_data = request.form.to_dict()
        action    = form_data.pop('action','draft')  # 'draft' or 'publish'
        errors    = validate_event(form_data)
 
        if errors:
            for e in errors: flash(e,'danger')
            return render_template('organizer/events/form.html',
                               form_data=form_data,venues=venues,action='create')
 
        status = 'published' if action == 'publish' else 'draft'
        start_dt = datetime.strptime(form_data['start_datetime'],FMT)
        end_dt   = datetime.strptime(form_data['end_datetime'],FMT)
 
        _,ref = db.collection('events').add({
            'name':           form_data['name'].strip(),
            'description':    form_data['description'].strip(),
            'start_datetime': start_dt,
            'end_datetime':   end_dt,
            'venue_id':       form_data['venue_id'],
            'event_type':     form_data.get('event_type','physical'),
            'status':         status,
            'organizer_uid':  session['uid'],
            'total_registrations': 0,
            'total_revenue':        0,
            'total_checkins':       0,
            'created_at':     SERVER_TIMESTAMP,
            'published_at':   SERVER_TIMESTAMP if status=='published' else None,
        })
 
        flash(f"Event '{form_data['name']}' {status}!",'success')
        return redirect(url_for('events.list_events'))
 
    return render_template('organizer/events/form.html',
                           form_data={},venues=venues,action='create')
 
 
# ── EDIT event ────────────────────────────────────────────────────────
@events_bp.route('/<event_id>/edit',methods=['GET','POST'])
@login_required
@role_required('organizer')
def edit_event(event_id):
    doc,data = get_event_or_403(event_id)
    if doc is None:
        flash('Event not found or access denied.','danger')
        return redirect(url_for('events.list_events'))
 
    venues = get_my_venues()
 
    # Convert timestamps to string for form pre-fill
    if data.get('start_datetime'):
        data['start_datetime'] = data['start_datetime'].strftime(FMT)
    if data.get('end_datetime'):
        data['end_datetime'] = data['end_datetime'].strftime(FMT)
 
    if request.method == 'POST':
        form_data = request.form.to_dict()
        form_data.pop('action',None)
        errors = validate_event(form_data)
 
        if errors:
            for e in errors: flash(e,'danger')
            return render_template('organizer/events/form.html',
                               form_data=form_data,venues=venues,
                               action='edit',event_id=event_id)
 
        start_dt = datetime.strptime(form_data['start_datetime'],FMT)
        end_dt   = datetime.strptime(form_data['end_datetime'],FMT)
 
        db.collection('events').document(event_id).update({
            'name':           form_data['name'].strip(),
            'description':    form_data['description'].strip(),
            'start_datetime': start_dt,
            'end_datetime':   end_dt,
            'venue_id':       form_data['venue_id'],
            'event_type':     form_data.get('event_type','physical'),
            'updated_at':     SERVER_TIMESTAMP,
        })
        flash(f"Event '{form_data['name']}' updated!",'success')
        return redirect(url_for('events.list_events'))
 
    return render_template('organizer/events/form.html',
                           form_data=data,venues=venues,
                           action='edit',event_id=event_id)
 
 
# ── PUBLISH event ─────────────────────────────────────────────────────
@events_bp.route('/<event_id>/publish',methods=['POST'])
@login_required
@role_required('organizer')
def publish_event(event_id):
    doc,data = get_event_or_403(event_id)
    if doc is None:
        flash('Event not found.','danger')
        return redirect(url_for('events.list_events'))
 
    db.collection('events').document(event_id).update({
        'status':       'published',
        'published_at': SERVER_TIMESTAMP
    })
    flash(f"Event '{data['name']}' is now published!",'success')
    return redirect(url_for('events.list_events'))
 
 
# ── DELETE event (soft delete — sets status to cancelled) ─────────────
@events_bp.route('/<event_id>/delete',methods=['POST'])
@login_required
@role_required('organizer')
def delete_event(event_id):
    doc,data = get_event_or_403(event_id)
    if doc is None:
        flash('Event not found.','danger')
        return redirect(url_for('events.list_events'))
 
    # Soft delete: mark as cancelled (preserves registration records)
    db.collection('events').document(event_id).update({
        'status': 'cancelled'
    })
    flash(f"Event '{data['name']}' has been cancelled.",'info')
    return redirect(url_for('events.list_events'))
# ── ATTENDEE LIST ───────────────────────────────────────────────────────
@events_bp.route('/<event_id>/attendees')
@login_required
@role_required('organizer')
def event_attendees(event_id):
    """Displays a table of all registrations for a specific event."""
    doc, data = get_event_or_403(event_id)
    if doc is None:
        flash('Event not found or access denied.', 'danger')
        return redirect(url_for('events.list_events'))

    # Fetch all registrations for this event
    regs = db.collection('registrations').where('event_id', '==', event_id).stream()
    attendees = [{**r.to_dict(), 'id': r.id} for r in regs]
    
    # Sort attendees by name in Python (avoids needing a complex Firestore index)
    attendees.sort(key=lambda x: x.get('attendee_name', '').lower())

    # FIXED: Added 'return' and changed 'event=event' to 'event=data'
    return render_template('organizer/events/attendees.html', event=data, attendees=attendees, event_id=event_id)

# ── EXPORT CSV ──────────────────────────────────────────────────────────
@events_bp.route('/<event_id>/export')
@login_required
@role_required('organizer')
def export_attendees(event_id):
    """Generates and downloads a CSV file of all attendees."""
    doc, data = get_event_or_403(event_id)
    if doc is None:
        return "Unauthorized", 403

    regs = db.collection('registrations').where('event_id', '==', event_id).stream()
    
    # Create an in-memory string buffer to build the CSV
    si = StringIO()
    # Add UTF-8 BOM so Microsoft Excel reads the Rupee symbol correctly
    si.write('\ufeff')
    cw = csv.writer(si)
    
    # Write the CSV Header row
    cw.writerow(['Order ID', 'Attendee Name', 'Email', 'Ticket Type', 'Quantity', 'Amount Paid', 'Status', 'Date'])
    
    # Write the data rows
    for r in regs:
        reg = r.to_dict()
        
        # Format the timestamp if it exists
        created_at = reg.get('created_at')
        date_str = created_at.strftime('%Y-%m-%d %H:%M') if created_at else 'N/A'
        
        cw.writerow([
            r.id,
            reg.get('attendee_name', ''),
            reg.get('attendee_email', ''),
            reg.get('ticket_type_name', ''),
            reg.get('quantity', 1),
            f"₹{reg.get('total_amount', 0)}",
            reg.get('status', '').upper(),
            date_str
        ])
        
    output = si.getvalue()
    
    # Return the CSV as a downloadable file
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=attendees_{event_id}.csv"}
    )

@events_bp.route('/<event_id>/waitlist')
@login_required
@role_required('organizer')
def view_waitlist(event_id):
    """View the waitlist for a specific event."""
    # 1. Verify ownership
    event_doc = db.collection('events').document(event_id).get()
    if not event_doc.exists or event_doc.to_dict().get('organizer_uid') != session.get('uid'):
        flash('Event not found or access denied.', 'danger')
        return redirect(url_for('events.list_events'))

    event_data = {**event_doc.to_dict(), 'id': event_doc.id}

    # 2. Fetch ticket types to map IDs to readable names
    tt_docs = db.collection('events').document(event_id).collection('ticket_types').stream()
    ticket_map = {tt.id: tt.to_dict().get('name', 'Unknown') for tt in tt_docs}

    # 3. Fetch the waitlist ordered by who joined first
    waitlist_docs = db.collection('events').document(event_id).collection('waitlist').order_by('joined_at').stream()
    waitlist = []
    for doc in waitlist_docs:
        w_data = doc.to_dict()
        w_data['id'] = doc.id
        w_data['ticket_name'] = ticket_map.get(w_data.get('ticket_type_id'), 'Unknown Ticket')
        waitlist.append(w_data)

    return render_template('organizer/events/waitlist.html', event=event_data, waitlist=waitlist)

@events_bp.route('/<event_id>/scanner')
@login_required
@role_required('organizer')
def event_scanner(event_id):
    """Render the QR code scanner page for an event."""
    event_doc = db.collection('events').document(event_id).get()
    
    if not event_doc.exists or event_doc.to_dict().get('organizer_uid') != session.get('uid'):
        flash('Event not found or access denied.', 'danger')
        return redirect(url_for('events.list_events'))
        
    event_data = {**event_doc.to_dict(), 'id': event_doc.id}
    
    return render_template('organizer/events/scanner.html', event=event_data)

@events_bp.route('/<event_id>/attendees/<reg_id>/toggle-checkin', methods=['POST'])
@login_required
@role_required('organizer')
def toggle_checkin(event_id, reg_id):
    """Manually toggle an attendee's check-in status."""
    reg_ref = db.collection('registrations').document(reg_id)
    reg_doc = reg_ref.get()
    
    if not reg_doc.exists or reg_doc.to_dict().get('event_id') != event_id:
        flash('Registration not found.', 'danger')
        return redirect(url_for('events.event_attendees', event_id=event_id))

    current_status = reg_doc.to_dict().get('status')
    
    # Determine new status and math
    if current_status == 'checked_in':
        new_status = 'confirmed'
        increment_val = -1
    else:
        new_status = 'checked_in'
        increment_val = 1

    # 1. Update the registration document
    reg_ref.update({'status': new_status})

    # 2. Update the event's total_checkins counter
    db.collection('events').document(event_id).update({
        'total_checkins': Increment(increment_val)
    })

    flash(f"Attendee successfully {'checked in' if new_status == 'checked_in' else 'un-checked in'}.", "success")
    return redirect(url_for('events.event_attendees', event_id=event_id))

@events_bp.route('/<event_id>/analytics')
@login_required
@role_required('organizer')
def event_analytics(event_id):
    """View visual analytics (charts) for an event."""
    event_doc = db.collection('events').document(event_id).get()
    if not event_doc.exists or event_doc.to_dict().get('organizer_uid') != session.get('uid'):
        flash('Event not found.', 'danger')
        return redirect(url_for('events.list_events'))

    # Fetch all confirmed or checked-in registrations
    regs = db.collection('registrations')\
             .where('event_id', '==', event_id)\
             .where('status', 'in', ['confirmed', 'checked_in']).stream()
    
    # Group ticket sales by ticket type name
    ticket_sales = {}
    for r in regs:
        data = r.to_dict()
        t_name = data.get('ticket_type_name', 'Unknown')
        qty = data.get('quantity', 1)
        ticket_sales[t_name] = ticket_sales.get(t_name, 0) + qty

    # Prepare data for Chart.js
    chart_labels = list(ticket_sales.keys())
    chart_data = list(ticket_sales.values())

    return render_template('organizer/events/analytics.html', 
                           event={**event_doc.to_dict(), 'id': event_id},
                           chart_labels=chart_labels, 
                           chart_data=chart_data)