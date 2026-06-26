from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.firebase_config import db
from app.decorators import login_required, role_required

promos_bp = Blueprint('promos', __name__, url_prefix='/organizer/events/<event_id>/promos')

@promos_bp.route('/')
@login_required
@role_required('organizer')
def list_promos(event_id):
    """List all promo codes for a specific event."""
    event_doc = db.collection('events').document(event_id).get()
    if not event_doc.exists or event_doc.to_dict().get('organizer_uid') != session.get('uid'):
        return redirect(url_for('events.list_events'))

    promos_docs = db.collection('events').document(event_id).collection('promo_codes').stream()
    promos = [{**d.to_dict(), 'id': d.id} for d in promos_docs]
    
    return render_template('organizer/promos/list.html', event=event_doc.to_dict(), event_id=event_id, promos=promos)

@promos_bp.route('/add', methods=['POST'])
@login_required
@role_required('organizer')
def add_promo(event_id):
    """Add a new promo code."""
    code = request.form.get('code').upper().strip()
    discount_pct = int(request.form.get('discount_percentage'))
    max_uses = int(request.form.get('max_uses', 0))

    if discount_pct < 1 or discount_pct > 100:
        flash('Discount must be between 1 and 100.', 'danger')
        return redirect(url_for('promos.list_promos', event_id=event_id))

    promo_data = {
        'code': code,
        'discount_percentage': discount_pct,
        'max_uses': max_uses,
        'current_uses': 0,
        'active': True
    }
    
    # Use the code itself as the document ID for easy lookup later
    db.collection('events').document(event_id).collection('promo_codes').document(code).set(promo_data)
    flash(f'Promo code {code} added successfully!', 'success')
    return redirect(url_for('promos.list_promos', event_id=event_id))

@promos_bp.route('/<code_id>/toggle', methods=['POST'])
@login_required
@role_required('organizer')
def toggle_promo(event_id, code_id):
    """Deactivate or reactivate a promo code."""
    doc_ref = db.collection('events').document(event_id).collection('promo_codes').document(code_id)
    doc = doc_ref.get()
    if doc.exists:
        current_status = doc.to_dict().get('active', True)
        doc_ref.update({'active': not current_status})
        flash('Promo code status updated.', 'info')
    return redirect(url_for('promos.list_promos', event_id=event_id))