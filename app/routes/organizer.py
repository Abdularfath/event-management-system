from flask import Blueprint, render_template, session
from app.firebase_config import db
from app.decorators import login_required, role_required
 
organizer_bp = Blueprint('organizer',__name__,url_prefix='/organizer')
 
 
@organizer_bp.route('/dashboard')
@login_required
@role_required('organizer')
def dashboard():
    # Fetch organizer's events
    docs = (
        db.collection('events')
        .where('organizer_uid','==',session['uid'])
        .order_by('created_at')
        .stream()
    )
    events = [{**d.to_dict(),'id':d.id} for d in docs]
 
    # Aggregate summary metrics across all events
    total_reg = sum(e.get('total_registrations',0) for e in events)
    total_rev = sum(e.get('total_revenue',0) for e in events)
    total_chk = sum(e.get('total_checkins',0) for e in events)
    published = sum(1 for e in events if e.get('status')=='published')
 
    return render_template('organizer/dashboard.html',
                           events=events,
                           total_reg=total_reg,
                           total_rev=total_rev,
                           total_chk=total_chk,
                           published=published)
