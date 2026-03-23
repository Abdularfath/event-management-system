from flask import (Blueprint, render_template, redirect,
                        url_for, session, flash, request)
from app.firebase_config import db
from app.decorators import login_required, role_required
from app.utils.validators import validate_venue
from datetime import datetime, timezone
from google.cloud.firestore import SERVER_TIMESTAMP
 
venues_bp = Blueprint('venues', __name__, url_prefix='/organizer/venues')
 
 
# ── Helper: get venue and verify ownership ───────────────────────────
def get_venue_or_404(venue_id):
    doc = db.collection('venues').document(venue_id).get()
    if not doc.exists:
        return None, None
    data = doc.to_dict()
    # Ownership check: only the organizer who created it can modify it
    if data.get('organizer_uid') != session.get('uid'):
        return None, 'forbidden'
    return doc, data
 
 
# ── LIST all venues for this organizer ───────────────────────────────
@venues_bp.route('/')
@login_required
@role_required('organizer')
def list_venues():
    # Query only venues owned by the logged-in organizer
    docs = (
        db.collection('venues')
        .where('organizer_uid', '==', session['uid'])
        .order_by('name')
        .stream()
    )
    venues = [{**d.to_dict(), 'id': d.id} for d in docs]
    return render_template('organizer/venues/list.html', venues=venues)
 
 
# ── CREATE new venue (GET = show form, POST = save) ──────────────────
@venues_bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('organizer')
def create_venue():
    if request.method == 'POST':
        form_data = request.form.to_dict()
        errors = validate_venue(form_data)
 
        if errors:
            for err in errors:
                flash(err, 'danger')
            return render_template('organizer/venues/form.html',
                               form_data=form_data, action='create')
 
        # Save to Firestore
        db.collection('venues').add({
            'name':          form_data['name'].strip(),
            'address':       form_data['address'].strip(),
            'city':          form_data['city'].strip(),
            'capacity':      int(form_data['capacity']),
            'contact_name':  form_data.get('contact_name', '').strip(),
            'contact_phone': form_data.get('contact_phone', '').strip(),
            'organizer_uid': session['uid'],
            'created_at':    SERVER_TIMESTAMP,
        })
 
        flash(f"Venue '{form_data['name']}' created successfully!", 'success')
        return redirect(url_for('venues.list_venues'))
 
    return render_template('organizer/venues/form.html',
                           form_data={}, action='create')
 
 
# ── EDIT existing venue ──────────────────────────────────────────────
@venues_bp.route('/<venue_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('organizer')
def edit_venue(venue_id):
    doc, data = get_venue_or_404(venue_id)
 
    if doc is None:
        flash('Venue not found or access denied.', 'danger')
        return redirect(url_for('venues.list_venues'))
 
    if request.method == 'POST':
        form_data = request.form.to_dict()
        errors = validate_venue(form_data)
 
        if errors:
            for err in errors:
                flash(err, 'danger')
            return render_template('organizer/venues/form.html',
                               form_data=form_data, action='edit', venue_id=venue_id)
 
        # Update only the editable fields (never overwrite organizer_uid or created_at)
        db.collection('venues').document(venue_id).update({
            'name':          form_data['name'].strip(),
            'address':       form_data['address'].strip(),
            'city':          form_data['city'].strip(),
            'capacity':      int(form_data['capacity']),
            'contact_name':  form_data.get('contact_name', '').strip(),
            'contact_phone': form_data.get('contact_phone', '').strip(),
            'updated_at':    SERVER_TIMESTAMP,
        })
 
        flash(f"Venue '{form_data['name']}' updated successfully!", 'success')
        return redirect(url_for('venues.list_venues'))
 
    # GET: pre-fill form with existing data
    return render_template('organizer/venues/form.html',
                           form_data=data, action='edit', venue_id=venue_id)
 
 
# ── DELETE venue ─────────────────────────────────────────────────────
@venues_bp.route('/<venue_id>/delete', methods=['POST'])
@login_required
@role_required('organizer')
def delete_venue(venue_id):
    doc, data = get_venue_or_404(venue_id)
 
    if doc is None:
        flash('Venue not found or access denied.', 'danger')
        return redirect(url_for('venues.list_venues'))
 
    venue_name = data.get('name', 'this venue')
    db.collection('venues').document(venue_id).delete()
    flash(f"Venue '{venue_name}' deleted.", 'info')
    return redirect(url_for('venues.list_venues'))
