from flask import Blueprint, render_template
from app.decorators import login_required, role_required
organizer_bp = Blueprint('organizer', __name__, url_prefix='/organizer')
 
@organizer_bp.route('/dashboard')
@login_required
@role_required('organizer')
def dashboard():
    return render_template('organizer/dashboard.html')
