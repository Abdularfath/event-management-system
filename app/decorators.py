from functools import wraps
from flask import session, redirect, url_for, flash
 
 
def login_required(f):
    """
    Decorator: redirect to login if user is not logged in.
    Usage:  @login_required  above any route function.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('uid'):
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated
 
 
def role_required(*roles):
    """
    Decorator: allow only users with specified role(s).
    Usage:  @role_required('organizer')  or  @role_required('organizer', 'admin')
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not session.get('uid'):
                flash('Please log in.', 'warning')
                return redirect(url_for('auth.login'))
            if session.get('role') not in roles:
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('public.index'))
            return f(*args, **kwargs)
        return decorated
    return decorator
