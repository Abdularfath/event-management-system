from flask import (Blueprint, render_template, redirect,
                        url_for, session, flash, request)
from app.firebase_config import db
from app.decorators import login_required, role_required
from app.utils.validators import validate_ticket_type
from google.cloud.firestore import SERVER_TIMESTAMP
 
tickets_bp = Blueprint('tickets',__name__,url_prefix='/organizer/events/<event_id>/tickets')
 
 
# ── Helper: verify organizer owns the event ──────────────────────────
def verify_event_ownership(event_id):
    """Returns (event_doc, event_data) or (None, None) if not found/forbidden."""
    doc = db.collection('events').document(event_id).get()
    if not doc.exists:
        return None, None
    data = doc.to_dict()
    if data.get('organizer_uid') != session.get('uid'):
        return None, None
    return doc, data
 
 
# ── Helper: get ticket type subcollection ref ────────────────────────
def tt_col(event_id):
    return (
        db.collection('events')
        .document(event_id)
        .collection('ticket_types')
    )
 
 
# ── LIST ticket types for an event ───────────────────────────────────
@tickets_bp.route('/')
@login_required
@role_required('organizer')
def list_tickets(event_id):
    event_doc, event_data = verify_event_ownership(event_id)
    if event_doc is None:
        flash('Event not found or access denied.','danger')
        return redirect(url_for('events.list_events'))
 
    docs = tt_col(event_id).order_by('name').stream()
    tickets = [{**d.to_dict(),'id':d.id} for d in docs]
 
    return render_template('organizer/tickets/list.html',
                           event=event_data, event_id=event_id,
                           tickets=tickets)
 
 
# ── CREATE ticket type ───────────────────────────────────────────────
@tickets_bp.route('/create',methods=['GET','POST'])
@login_required
@role_required('organizer')
def create_ticket(event_id):
    event_doc, event_data = verify_event_ownership(event_id)
    if event_doc is None:
        flash('Event not found or access denied.','danger')
        return redirect(url_for('events.list_events'))
 
    if request.method == 'POST':
        form_data = request.form.to_dict()
        errors = validate_ticket_type(form_data)
 
        if errors:
            for e in errors: flash(e,'danger')
            return render_template('organizer/tickets/form.html',
                               event=event_data,event_id=event_id,
                               form_data=form_data,action='create')
 
        tt_col(event_id).add({
            'name':           form_data['name'].strip(),
            'description':    form_data.get('description','').strip(),
            'price':          float(form_data['price']),
            'quantity_total': int(form_data['quantity_total']),
            'quantity_sold':  0,
            'max_per_order':  int(form_data['max_per_order']),
            'is_active':      True,
            'created_at':     SERVER_TIMESTAMP,
        })
 
        flash(f"Ticket '{form_data['name']}' created!",'success')
        return redirect(url_for('tickets.list_tickets',event_id=event_id))
 
    return render_template('organizer/tickets/form.html',
                           event=event_data,event_id=event_id,
                           form_data={},action='create')
 
 
# ── EDIT ticket type ──────────────────────────────────────────────────
@tickets_bp.route('/<tt_id>/edit',methods=['GET','POST'])
@login_required
@role_required('organizer')
def edit_ticket(event_id, tt_id):
    event_doc, event_data = verify_event_ownership(event_id)
    if event_doc is None:
        flash('Event not found or access denied.','danger')
        return redirect(url_for('events.list_events'))
 
    tt_doc = tt_col(event_id).document(tt_id).get()
    if not tt_doc.exists:
        flash('Ticket type not found.','danger')
        return redirect(url_for('tickets.list_tickets',event_id=event_id))
 
    tt_data = tt_doc.to_dict()
    # Convert numbers to strings for form pre-fill
    tt_data['price'] = str(tt_data.get('price',0))
    tt_data['quantity_total'] = str(tt_data.get('quantity_total',0))
    tt_data['max_per_order'] = str(tt_data.get('max_per_order',1))
 
    if request.method == 'POST':
        form_data = request.form.to_dict()
        errors = validate_ticket_type(form_data)
 
        if errors:
            for e in errors: flash(e,'danger')
            return render_template('organizer/tickets/form.html',
                               event=event_data,event_id=event_id,
                               form_data=form_data,action='edit',tt_id=tt_id)
 
        # Prevent reducing quantity below sold count
        new_qty = int(form_data['quantity_total'])
        sold    = tt_doc.to_dict().get('quantity_sold',0)
        if new_qty < sold:
            flash(f'Cannot reduce quantity below {sold} (already sold).','danger')
            return redirect(url_for('tickets.list_tickets',event_id=event_id))
 
        tt_col(event_id).document(tt_id).update({
            'name':           form_data['name'].strip(),
            'description':    form_data.get('description','').strip(),
            'price':          float(form_data['price']),
            'quantity_total': new_qty,
            'max_per_order':  int(form_data['max_per_order']),
            'updated_at':     SERVER_TIMESTAMP,
        })
        flash(f"Ticket '{form_data['name']}' updated!",'success')
        return redirect(url_for('tickets.list_tickets',event_id=event_id))
 
    return render_template('organizer/tickets/form.html',
                           event=event_data,event_id=event_id,
                           form_data=tt_data,action='edit',tt_id=tt_id)
 
 
# ── DELETE ticket type ───────────────────────────────────────────────
@tickets_bp.route('/<tt_id>/delete',methods=['POST'])
@login_required
@role_required('organizer')
def delete_ticket(event_id, tt_id):
    event_doc, event_data = verify_event_ownership(event_id)
    if event_doc is None:
        flash('Event not found or access denied.','danger')
        return redirect(url_for('events.list_events'))
 
    tt_doc = tt_col(event_id).document(tt_id).get()
    if not tt_doc.exists:
        flash('Ticket type not found.','danger')
        return redirect(url_for('tickets.list_tickets',event_id=event_id))
 
    # Block delete if tickets have been sold
    sold = tt_doc.to_dict().get('quantity_sold',0)
    if sold > 0:
        flash(f'{sold} tickets already sold. Cannot delete this ticket type.','danger')
        return redirect(url_for('tickets.list_tickets',event_id=event_id))
 
    tt_name = tt_doc.to_dict().get('name','this ticket')
    tt_col(event_id).document(tt_id).delete()
    flash(f"Ticket '{tt_name}' deleted.",'info')
    return redirect(url_for('tickets.list_tickets',event_id=event_id))
 
 
# ── TOGGLE is_active ──────────────────────────────────────────────────
@tickets_bp.route('/<tt_id>/toggle',methods=['POST'])
@login_required
@role_required('organizer')
def toggle_ticket(event_id, tt_id):
    event_doc, _ = verify_event_ownership(event_id)
    if event_doc is None:
        return redirect(url_for('events.list_events'))
 
    tt_ref = tt_col(event_id).document(tt_id)
    tt_doc = tt_ref.get()
    if tt_doc.exists:
        current = tt_doc.to_dict().get('is_active',True)
        tt_ref.update({'is_active': not current})
        status = 'enabled' if not current else 'disabled'
        flash(f'Ticket {status}.','info')
    return redirect(url_for('tickets.list_tickets',event_id=event_id))
