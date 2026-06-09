from flask import (Blueprint, render_template, request,
                   redirect, url_for, flash, session)
from app.firebase_config import db
from app.decorators import login_required, role_required
from google.cloud.firestore import SERVER_TIMESTAMP

super_admin_bp = Blueprint('super_admin', __name__, url_prefix='/superadmin')


# ── DASHBOARD ────────────────────────────────────────────────────────
@super_admin_bp.route('/dashboard')
@login_required
@role_required('super_admin')
def dashboard():
    # Fetch all tenants
    tenants_docs = db.collection('tenants').stream()
    tenants = [{**t.to_dict(), 'id': t.id} for t in tenants_docs]

    total_tenants  = len(tenants)
    active_tenants = sum(1 for t in tenants if t.get('status') == 'active')

    # Platform-wide stats
    total_events        = 0
    total_registrations = 0
    total_revenue       = 0.0
    total_users         = 0

    # Count all events across platform
    all_events = db.collection('events').stream()
    for e in all_events:
        total_events += 1

    # Count all registrations and revenue
    all_regs = db.collection('registrations')\
                 .where('status', 'in', ['confirmed', 'checked_in']).stream()
    for r in all_regs:
        reg_data = r.to_dict()
        total_registrations += 1
        total_revenue += float(reg_data.get('total_amount', 0))

    # Count all users
    all_users = db.collection('users').stream()
    for u in all_users:
        total_users += 1

    return render_template(
        'super_admin/dashboard.html',
        tenants=tenants,
        total_tenants=total_tenants,
        active_tenants=active_tenants,
        total_events=total_events,
        total_registrations=total_registrations,
        total_revenue=total_revenue,
        total_users=total_users
    )


# ── TENANT LIST ──────────────────────────────────────────────────────
@super_admin_bp.route('/tenants')
@login_required
@role_required('super_admin')
def list_tenants():
    tenants_docs = db.collection('tenants').stream()
    tenants = [{**t.to_dict(), 'id': t.id} for t in tenants_docs]
    tenants.sort(key=lambda x: x.get('company_name', '').lower())
    return render_template('super_admin/tenants.html', tenants=tenants)


# ── CREATE TENANT ────────────────────────────────────────────────────
@super_admin_bp.route('/tenants/create', methods=['GET', 'POST'])
@login_required
@role_required('super_admin')
def create_tenant():
    if request.method == 'POST':
        company_name   = request.form.get('company_name', '').strip()
        contact_person = request.form.get('contact_person', '').strip()
        contact_email  = request.form.get('contact_email', '').strip()
        phone          = request.form.get('phone', '').strip()

        if not company_name or not contact_email:
            flash('Company name and contact email are required.', 'danger')
            return redirect(url_for('super_admin.create_tenant'))

        # Check if tenant already exists
        existing = db.collection('tenants')\
                     .where('contact_email', '==', contact_email)\
                     .limit(1).stream()
        if list(existing):
            flash('A tenant with this email already exists.', 'warning')
            return redirect(url_for('super_admin.create_tenant'))

        tenant_data = {
            'company_name':   company_name,
            'contact_person': contact_person,
            'contact_email':  contact_email,
            'phone':          phone,
            'status':         'active',
            'created_at':     SERVER_TIMESTAMP,
            'admin_uid':      ''
        }

        db.collection('tenants').add(tenant_data)
        flash(f'Tenant {company_name} created successfully!', 'success')
        return redirect(url_for('super_admin.list_tenants'))

    return render_template('super_admin/tenants.html',
                           tenants=[], show_form=True)


# ── TOGGLE TENANT STATUS ─────────────────────────────────────────────
@super_admin_bp.route('/tenants/<tenant_id>/toggle', methods=['POST'])
@login_required
@role_required('super_admin')
def toggle_tenant(tenant_id):
    tenant_ref = db.collection('tenants').document(tenant_id)
    tenant_doc = tenant_ref.get()

    if not tenant_doc.exists:
        flash('Tenant not found.', 'danger')
        return redirect(url_for('super_admin.list_tenants'))

    current = tenant_doc.to_dict().get('status', 'active')
    new_status = 'suspended' if current == 'active' else 'active'
    tenant_ref.update({'status': new_status})

    flash(f'Tenant status updated to {new_status}.', 'success')
    return redirect(url_for('super_admin.list_tenants'))


# ── TENANT DETAIL ────────────────────────────────────────────────────
@super_admin_bp.route('/tenants/<tenant_id>')
@login_required
@role_required('super_admin')
def tenant_detail(tenant_id):
    tenant_doc = db.collection('tenants').document(tenant_id).get()
    if not tenant_doc.exists:
        flash('Tenant not found.', 'danger')
        return redirect(url_for('super_admin.list_tenants'))

    tenant = {**tenant_doc.to_dict(), 'id': tenant_doc.id}

    # Find admin user for this tenant
    admin_user = None
    if tenant.get('admin_uid'):
        admin_doc = db.collection('users')\
                      .document(tenant['admin_uid']).get()
        if admin_doc.exists:
            admin_user = {**admin_doc.to_dict(), 'id': admin_doc.id}

    # Find all organizers linked to this tenant
    organizers = []
    org_docs = db.collection('users')\
                 .where('tenant_id', '==', tenant_id)\
                 .where('role', '==', 'organizer').stream()
    for o in org_docs:
        organizers.append({**o.to_dict(), 'id': o.id})

    # Count events for this tenant
    tenant_events = []
    if organizers:
        org_uids = [o['id'] for o in organizers]
        all_events = db.collection('events').stream()
        for e in all_events:
            e_data = {**e.to_dict(), 'id': e.id}
            if e_data.get('organizer_uid') in org_uids:
                tenant_events.append(e_data)

    total_revenue = 0
    total_regs    = 0
    if tenant_events:
        event_ids = [e['id'] for e in tenant_events]
        all_regs = db.collection('registrations')\
                     .where('status', 'in', ['confirmed', 'checked_in'])\
                     .stream()
        for r in all_regs:
            r_data = r.to_dict()
            if r_data.get('event_id') in event_ids:
                total_regs    += 1
                total_revenue += float(r_data.get('total_amount', 0))

    return render_template(
        'super_admin/tenant_detail.html',
        tenant=tenant,
        admin_user=admin_user,
        organizers=organizers,
        tenant_events=tenant_events,
        total_revenue=total_revenue,
        total_regs=total_regs
    )


# ── ALL USERS ACROSS PLATFORM ────────────────────────────────────────
@super_admin_bp.route('/users')
@login_required
@role_required('super_admin')
def all_users():
    search = request.args.get('q', '').strip().lower()

    users_docs = db.collection('users').stream()
    users = []
    for u in users_docs:
        data = {**u.to_dict(), 'id': u.id}
        if search:
            searchable = f"{data.get('email','')} {data.get('name','')}".lower()
            if search not in searchable:
                continue
        users.append(data)

    users.sort(key=lambda x: x.get('email', '').lower())

    return render_template('super_admin/users.html',
                           users=users, search=search)


# ── TOGGLE USER STATUS ───────────────────────────────────────────────
@super_admin_bp.route('/users/<uid>/toggle', methods=['POST'])
@login_required
@role_required('super_admin')
def toggle_user(uid):
    user_ref = db.collection('users').document(uid)
    user_doc = user_ref.get()

    if not user_doc.exists:
        flash('User not found.', 'danger')
        return redirect(url_for('super_admin.all_users'))

    # Prevent super admin from suspending themselves
    if uid == session.get('uid'):
        flash('You cannot suspend your own account.', 'danger')
        return redirect(url_for('super_admin.all_users'))

    current = user_doc.to_dict().get('status', 'active')
    new_status = 'suspended' if current == 'active' else 'active'
    user_ref.update({'status': new_status})

    flash(f'User status updated to {new_status}.', 'success')
    return redirect(url_for('super_admin.all_users'))