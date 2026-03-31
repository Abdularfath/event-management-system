import os, secrets
from flask import (Blueprint, render_template, redirect,
                        url_for, session, flash, request, jsonify, abort)
from app.firebase_config import db
from app.decorators import login_required
from datetime import datetime, timezone
from google.cloud.firestore import SERVER_TIMESTAMP, Increment
 
registration_bp = Blueprint('registration',__name__,url_prefix='/register')
 
 
# ── Helper: fetch event + ticket type + verify availability ──────────
def get_event_and_ticket(event_id, ticket_type_id):
    """Returns (event_data, ticket_data) or aborts with 404."""
    event_doc = db.collection('events').document(event_id).get()
    if not event_doc.exists or event_doc.to_dict().get('status') != 'published':
        abort(404)
 
    tt_doc = (
        db.collection('events')
        .document(event_id)
        .collection('ticket_types')
        .document(ticket_type_id)
        .get()
    )
    if not tt_doc.exists:
        abort(404)
 
    event  = {**event_doc.to_dict(), 'id': event_doc.id}
    ticket = {**tt_doc.to_dict(),  'id': tt_doc.id}
    return event, ticket
 
 
# ── Helper: apply promo code discount ────────────────────────────────
def apply_promo(event_id, code, subtotal):
    """Returns (discount_amount, promo_doc_id, error_msg)."""
    from datetime import timezone
    now = datetime.now(timezone.utc)
 
    docs = (
        db.collection('promo_codes')
        .where('event_id','==',event_id)
        .where('code','==',code.upper())
        .where('is_active','==',True)
        .limit(1).stream()
    )
    results = list(docs)
    if not results:
        return 0, None, 'Invalid promo code.'
 
    promo_doc = results[0]
    promo = promo_doc.to_dict()
 
    # Check validity dates
    if promo.get('valid_from') and now < promo['valid_from']:
        return 0, None, 'Promo code is not yet active.'
    if promo.get('valid_until') and now > promo['valid_until']:
        return 0, None, 'Promo code has expired.'
 
    # Check usage limit
    used  = promo.get('used_count',0)
    limit = promo.get('max_uses',0)
    if limit > 0 and used >= limit:
        return 0, None, 'Promo code usage limit reached.'
 
    # Calculate discount
    dtype = promo.get('discount_type','fixed')
    dval  = promo.get('discount_value',0)
    if dtype == 'percentage':
        discount = round(subtotal * dval / 100, 2)
    else:
        discount = min(dval, subtotal)  # cannot discount more than subtotal
 
    return discount, promo_doc.id, None
 
 
# ── REGISTRATION FORM — GET shows form, POST creates pending reg ──────
@registration_bp.route('/<event_id>/<ticket_type_id>',methods=['GET','POST'])
@login_required
def register(event_id, ticket_type_id):
    event, ticket = get_event_and_ticket(event_id, ticket_type_id)
 
    # Check ticket availability
    available = ticket.get('quantity_total',0) - ticket.get('quantity_sold',0)
    if available <= 0:
        flash('Sorry, this ticket type is sold out.','warning')
        return redirect(url_for('public.event_detail',event_id=event_id))
 
    if request.method == 'POST':
        quantity = int(request.form.get('quantity','1'))
        promo_code  = request.form.get('promo_code','').strip()
 
        # Server-side quantity validation
        max_order = ticket.get('max_per_order',10)
        if quantity < 1 or quantity > min(max_order, available):
            flash(f'Please select between 1 and {min(max_order,available)} tickets.','danger')
            return redirect(request.url)
 
        subtotal = round(ticket['price'] * quantity, 2)
        discount = 0
        promo_id = None
 
        # Apply promo code if provided
        if promo_code:
            discount, promo_id, err = apply_promo(event_id, promo_code, subtotal)
            if err:
                flash(err, 'warning')
                discount = 0
                promo_id = None
                promo_code = ''
 
        total_amount = max(0, subtotal - discount)
 
        # Create PENDING registration in Firestore
        user_doc = db.collection('users').document(session['uid']).get()
        user_data = user_doc.to_dict() if user_doc.exists else {}
 
        _,reg_ref = db.collection('registrations').add({
            'event_id':         event_id,
            'attendee_uid':      session['uid'],
            'attendee_name':     user_data.get('full_name', session.get('email','').split('@')[0]),
            'attendee_email':    session['email'],
            'ticket_type_id':    ticket_type_id,
            'ticket_type_name':  ticket['name'],
            'quantity':          quantity,
            'unit_price':        ticket['price'],
            'subtotal':          subtotal,
            'discount_amount':   discount,
            'total_amount':      total_amount,
            'promo_code_used':   promo_code or None,
            'status':            'pending',
            'payment_status':    'pending',
            'order_number':      f'ORD-{secrets.token_hex(4).upper()}',
            'created_at':        SERVER_TIMESTAMP,
        })
 
        # If ticket is free — skip payment, confirm immediately
        if total_amount == 0:
            reg_ref.update({
                'status':         'confirmed',
                'payment_status': 'paid',
                'confirmed_at':   SERVER_TIMESTAMP,
            })
            db.collection('events').document(event_id).update({
                'total_registrations': Increment(1)
            })
            db.collection('events').document(event_id).collection('ticket_types').document(ticket_type_id).update({
                'quantity_sold': Increment(quantity)
            })
            flash('Registration confirmed! This is a free ticket.','success')
            return redirect(url_for('attendee.my_events'))
 
        # Paid ticket — go to payment summary
        return redirect(url_for('registration.payment_summary',
                               registration_id=reg_ref.id))
 
    # GET — show the registration form
    return render_template('attendee/register.html',
                           event=event,ticket=ticket,available=available)
 
 
# ── PROMO CODE VALIDATION API — called by JavaScript ─────────────────
@registration_bp.route('/validate-promo',methods=['POST'])
@login_required
def validate_promo():
    """JSON endpoint for live promo code validation."""
    data       = request.json
    event_id   = data.get('event_id','')
    code       = data.get('code','').strip()
    subtotal   = float(data.get('subtotal',0))
 
    if not code:
        return jsonify({'valid':False,'message':'Enter a promo code.'})
 
    discount, _, err = apply_promo(event_id, code, subtotal)
    if err:
        return jsonify({'valid':False,'message':err})
 
    return jsonify({
        'valid':True,
        'message':f'Promo applied! You save ₹{discount}',
        'discount':discount,
        'new_total':round(max(0,subtotal-discount),2)
    })
 
 
# ── PAYMENT SUMMARY PAGE ─────────────────────────────────────────────
@registration_bp.route('/payment/<registration_id>')
@login_required
def payment_summary(registration_id):
    reg_doc = db.collection('registrations').document(registration_id).get()
    if not reg_doc.exists:
        abort(404)
 
    reg = reg_doc.to_dict()
 
    # Security: only the attendee who created this registration can view it
    if reg.get('attendee_uid') != session.get('uid'):
        abort(403)
 
    # Guard: already paid registrations should not re-show payment page
    if reg.get('payment_status') == 'paid':
        flash('This registration is already paid.','info')
        return redirect(url_for('attendee.my_events'))
 
    event_doc = db.collection('events').document(reg['event_id']).get()
    event = event_doc.to_dict() if event_doc.exists else {}
 
    return render_template('attendee/payment_summary.html',
                           reg=reg,
                           registration_id=registration_id,
                           event=event)
