from flask import (Blueprint, render_template, request,
                        abort, flash, redirect, url_for, session)
from app.firebase_config import db
 
public_bp = Blueprint('public', __name__)
 
 
# ── PUBLIC HOME — event listing ─────────────────────────────────────
@public_bp.route('/')
def index():
    search = request.args.get('q', '').strip().lower()
 
    # Fetch all published events ordered by start date
    docs = (
        db.collection('events')
        .where('status', '==', 'published')
        .order_by('start_datetime')
        .stream()
    )
 
    events = []
    for doc in docs:
        data = {**doc.to_dict(), 'id': doc.id}
 
        # Get venue name for display on the card
        venue_name = 'Venue TBD'
        if data.get('venue_id'):
            v = db.collection('venues').document(data['venue_id']).get()
            if v.exists:
                venue_name = v.to_dict().get('name', 'Unknown Venue')
        data['venue_name'] = venue_name
 
        # Client-side keyword search filter
        if search:
            searchable = f"{data.get('name','')} {venue_name}".lower()
            if search not in searchable:
                continue
 
        events.append(data)
 
    return render_template('public/index.html',
                           events=events, search=search)
 
 
# ── EVENT DETAIL PAGE ───────────────────────────────────────────────
@public_bp.route('/events/<event_id>')
def event_detail(event_id):
    # Fetch the event document
    doc = db.collection('events').document(event_id).get()
    if not doc.exists:
        abort(404)
 
    event = {**doc.to_dict(), 'id': doc.id}
 
    # Only show published events to the public
    if event.get('status') != 'published':
        abort(404)
 
    # Fetch venue details
    venue = None
    if event.get('venue_id'):
        v = db.collection('venues').document(event['venue_id']).get()
        if v.exists:
            venue = v.to_dict()
 
    # Fetch ticket types from subcollection
    ticket_docs = (
        db.collection('events')
        .document(event_id)
        .collection('ticket_types')
        .where('is_active', '==', True)
        .stream()
    )
    ticket_types = [{**t.to_dict(), 'id': t.id} for t in ticket_docs]
 
    # Calculate availability for each ticket type
    for tt in ticket_types:
        available = tt.get('quantity_total', 0) - tt.get('quantity_sold', 0)
        tt['available'] = max(0, available)
        tt['sold_out']  = available <= 0
 
    return render_template('public/event_detail.html',
                           event=event,
                           venue=venue,
                           ticket_types=ticket_types)

