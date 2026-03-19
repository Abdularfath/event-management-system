from flask import Blueprint, render_template
from app.decorators import login_required
attendee_bp = Blueprint('attendee', __name__, url_prefix='/attendee')
 
@attendee_bp.route('/my-events')
@login_required
def my_events():
    return render_template('attendee/my_events.html')
