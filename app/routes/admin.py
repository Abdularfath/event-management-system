from flask import Blueprint, render_template, redirect, url_for, flash, session, request
from app.firebase_config import db
from app.decorators import login_required, role_required

# Create the blueprint for admin routes
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/dashboard')
@login_required
@role_required('admin')  # Only users with the 'admin' role can access this!
def dashboard():
    """Display a list of all users in the system."""
    users_ref = db.collection('users').stream()
    users = [{**u.to_dict(), 'id': u.id} for u in users_ref]
    
    return render_template('admin/dashboard.html', users=users)

@admin_bp.route('/user/<uid>/toggle', methods=['POST'])
@login_required
@role_required('admin')
def toggle_user(uid):
    """Suspend or Activate a user account."""
    user_ref = db.collection('users').document(uid)
    user_doc = user_ref.get()
    
    if user_doc.exists:
        current_status = user_doc.to_dict().get('status', 'active')
        new_status = 'suspended' if current_status == 'active' else 'active'
        user_ref.update({'status': new_status})
        flash(f"User account is now {new_status}.", "success")
    else:
        flash("User not found.", "danger")
        
    return redirect(url_for('admin.dashboard'))