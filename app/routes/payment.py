"""
Payment routes for Razorpay integration.
Handles order creation, payment capture, and success/failure flows.
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session
from app.firebase_config import db, auth
from app.decorators import login_required
from app.utils.razorpay_utils import (
    create_razorpay_order,
    verify_payment_signature,
    get_payment_details
)
import os
from dotenv import load_dotenv
from google.cloud.firestore import Increment  # ← ADD THIS if missing
from flask import render_template
from app.utils.qr_utils import generate_and_upload_qr
from app.utils.email_utils import send_ticket_email

load_dotenv()

payment_bp = Blueprint('payment', __name__, url_prefix='/attendee/payment')


# ── HELPER: Verify registration ownership ──────────────────────────
def verify_registration_owner(registration_id, user_uid):
    """
    Security check: ensure the logged-in user owns this registration.
    """
    try:
        reg_doc = db.collection('registrations').document(registration_id).get()
        if not reg_doc.exists:
            return False, "Registration not found"
        
        reg_data = reg_doc.to_dict()
        if reg_data.get('attendee_uid') != user_uid:  # ✅ Compare with attendee_uid
            return False, "Unauthorized"
        
        return True, reg_data
    except Exception as e:
        return False, str(e)


# ── CREATE ORDER: Called when user clicks "Pay Now" ──────────────────
@payment_bp.route('/<registration_id>/create-order', methods=['POST'])
@login_required
def create_order(registration_id):
    """
    Create a Razorpay order for this registration.
    Called via AJAX from payment_summary.html
    
    Returns:
        JSON with order details to pass to Razorpay Checkout
    """
    user_uid = session.get('uid')
    
    # Security: verify user owns this registration
    owns, result = verify_registration_owner(registration_id, user_uid)
    if not owns:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    reg_data = result
    
    # Get registration details
    attendee_email = reg_data.get('attendee_email', '')
    total_amount = reg_data.get('total_amount', 0)  # in ₹
    
    # Convert ₹ to paise (₹100 = 10000 paise)
    amount_in_paise = int(total_amount * 100)
    
    # Create Razorpay order
    order_result = create_razorpay_order(
        amount_in_paise,
        registration_id,
        attendee_email
    )
    
    if not order_result['success']:
        return jsonify({'success': False, 'error': order_result['error']}), 500
    
    # Return order details for Razorpay Checkout
    return jsonify({
        'success': True,
        'order_id': order_result['order_id'],
        'amount': order_result['amount'],
        'currency': order_result['currency'],
        'key_id': os.getenv('RAZORPAY_KEY_ID'),
        'registration_id': registration_id,
        'email': attendee_email
    })


# ── CAPTURE PAYMENT: Called after user approves in Razorpay checkout ──
@payment_bp.route('/<registration_id>/capture', methods=['POST'])
@login_required
def capture_payment(registration_id):
    """
    Capture the payment after user completes Razorpay checkout.
    """
    user_uid = session.get('uid')
    print(f"[DEBUG CAPTURE] Starting capture for user {user_uid}")
    
    # Security: verify user owns this registration
    owns, result = verify_registration_owner(registration_id, user_uid)
    if not owns:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    reg_data = result
    
    # Get payment data from request
    data = request.get_json()
    razorpay_order_id = data.get('razorpay_order_id')
    razorpay_payment_id = data.get('razorpay_payment_id')
    razorpay_signature = data.get('razorpay_signature')
    
    # Step 1: Verify Razorpay signature
    sig_valid = verify_payment_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature)
    if not sig_valid:
        return jsonify({'success': False, 'error': 'Payment verification failed'}), 400
    
    # Step 2: Fetch payment details
    payment_details = get_payment_details(razorpay_payment_id)
    if not payment_details['success']:
        return jsonify({'success': False, 'error': 'Could not fetch payment details'}), 500
    
    # Step 3: Verify amount
    captured_amount = payment_details['amount'] / 100
    expected_amount = reg_data.get('total_amount', 0)
    
    if abs(captured_amount - expected_amount) > 0.01:
        return jsonify({'success': False, 'error': 'Amount mismatch'}), 400
    
    # ── NEW: Generate and Upload QR Code to Cloudinary ──
    print(f"[DEBUG CAPTURE] Generating QR code...")
    event_id = reg_data.get('event_id')
    qr_url, qr_payload = generate_and_upload_qr(registration_id, event_id)
    print(f"[DEBUG CAPTURE] QR URL: {qr_url}")
    
    # Step 4: Update registration in Firestore
    try:
        db.collection('registrations').document(registration_id).update({
            'status': 'confirmed',
            'payment_status': 'paid',
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_order_id': razorpay_order_id,
            'qr_code_url': qr_url,       # Save Cloudinary URL
            'qr_payload': qr_payload     # Save secure HMAC payload
        })
        print(f"[DEBUG CAPTURE] Registration updated ✓")
    except Exception as e:
        print(f"[ERROR CAPTURE] Registration update failed: {str(e)}")
        return jsonify({'success': False, 'error': 'Database update failed'}), 500
    
    # Step 5: Increment event counters
    try:
        quantity = int(reg_data.get('quantity', 1))
        ticket_type_id = reg_data.get('ticket_type_id')
        
        # Update event
        db.collection('events').document(event_id).update({
            'total_registrations': Increment(1),
            'total_revenue': Increment(captured_amount)
        })
        
        # Update ticket type
        if ticket_type_id:
            db.collection('events').document(event_id).collection('ticket_types').document(ticket_type_id).update({
                'quantity_sold': Increment(quantity)
            })
    except Exception as e:
        print(f"[ERROR CAPTURE] Counter update failed: {str(e)}")

    # ── NEW: Send Confirmation Email ──
    print(f"[DEBUG CAPTURE] Sending confirmation email...")
    try:
        # Fetch the fully updated registration so it contains the qr_code_url
        updated_reg_doc = db.collection('registrations').document(registration_id).get()
        updated_reg = updated_reg_doc.to_dict()
        
        # Fetch event details for the email template
        event_doc = db.collection('events').document(event_id).get()
        event_data = event_doc.to_dict() if event_doc.exists else {}
        
        # Render the HTML email template
        email_html = render_template(
            'emails/confirmation.html',
            registration=updated_reg,
            event=event_data,
            registration_id=registration_id,
            qr_url=qr_url 
        )
        
        # Send Email
        email_sent = send_ticket_email(
            to_email=updated_reg.get('attendee_email'),
            subject=f"Your Ticket for {event_data.get('name', 'Event')}",
            html_content=email_html
        )
        print(f"[DEBUG CAPTURE] Email sent status: {email_sent}")
    except Exception as e:
        print(f"[ERROR CAPTURE] Failed to send confirmation email: {e}")
    
    print(f"[DEBUG CAPTURE] Capture complete ✓")
    return jsonify({
        'success': True,
        'registration_id': registration_id,
        'message': 'Payment captured successfully'
    })

# ── PAYMENT SUCCESS PAGE ───────────────────────────────────────────
@payment_bp.route('/success/<registration_id>')
@login_required
def payment_success(registration_id):
    """
    Display success page after payment.
    Shows registration details and QR code.
    """
    user_uid = session.get('uid')
    
    # Security: verify user owns this registration
    owns, result = verify_registration_owner(registration_id, user_uid)
    if not owns:
        flash('Unauthorized', 'error')
        return redirect(url_for('public.index'))
    
    reg_data = result
    
    # Fetch event details for context
    try:
        event_id = reg_data.get('event_id')
        event_doc = db.collection('events').document(event_id).get()
        event_data = event_doc.to_dict() if event_doc.exists else {}
        event_data['id'] = event_doc.id  # ✅ ADD THIS - Include ID for template
        event_data['_id'] = event_doc.id  # ✅ Also add _id for backward compatibility
        print(f"[DEBUG] Success page - Event ID: {event_data.get('id')}")
    except Exception as e:
        event_data = {}
    
    return render_template('attendee/success.html',
        registration=reg_data,
        registration_id=registration_id,
        event=event_data,
        order_number=reg_data.get('razorpay_order_id', 'N/A')
    )


# ── PAYMENT FAILURE HANDLER ────────────────────────────────────────
@payment_bp.route('/failed/<registration_id>')
@login_required
def payment_failed(registration_id):
    """
    Handle payment failure.
    Allows user to retry.
    """
    user_uid = session.get('uid')
    
    owns, result = verify_registration_owner(registration_id, user_uid)
    if not owns:
        flash('Unauthorized', 'error')
        return redirect(url_for('public.index'))
    
    reg_data = result
    
    # Mark registration as failed
    try:
        db.collection('registrations').document(registration_id).update({
            'payment_status': 'failed'
        })
    except:
        pass
    
    flash('Payment failed. Please try again.', 'error')
    return redirect(url_for('payment.payment_summary', registration_id=registration_id))