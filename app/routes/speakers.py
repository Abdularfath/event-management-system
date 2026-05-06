from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.firebase_config import db
from app.decorators import login_required, role_required
import cloudinary.uploader

speakers_bp = Blueprint('speakers', __name__, url_prefix='/organizer/speakers')

@speakers_bp.route('/')
@login_required
@role_required('organizer')
def list_speakers():
    """List all speakers belonging to this organizer."""
    docs = db.collection('speakers').where('organizer_uid', '==', session.get('uid')).stream()
    speakers = [{**d.to_dict(), 'id': d.id} for d in docs]
    return render_template('organizer/speakers/list.html', speakers=speakers)

@speakers_bp.route('/add', methods=['GET', 'POST'])
@login_required
@role_required('organizer')
def add_speaker():
    if request.method == 'POST':
        name = request.form.get('name')
        bio = request.form.get('bio')
        company = request.form.get('company')
        image_file = request.files.get('image')
        
        image_url = ""
        if image_file:
            # Upload to Cloudinary and AUTO-CROP to the face!
            upload_result = cloudinary.uploader.upload(
                image_file,
                folder="ems_speakers",
                width=200,
                height=200,
                crop="fill",
                gravity="face"
            )
            image_url = upload_result.get('secure_url')

        speaker_data = {
            'organizer_uid': session.get('uid'),
            'name': name,
            'bio': bio,
            'company': company,
            'image_url': image_url
        }
        
        db.collection('speakers').add(speaker_data)
        flash('Speaker added successfully!', 'success')
        return redirect(url_for('speakers.list_speakers'))

    return render_template('organizer/speakers/form.html')

@speakers_bp.route('/<speaker_id>/delete', methods=['POST'])
@login_required
@role_required('organizer')
def delete_speaker(speaker_id):
    db.collection('speakers').document(speaker_id).delete()
    flash('Speaker deleted.', 'info')
    return redirect(url_for('speakers.list_speakers'))