import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app import db
from app.models.user_email import UserEmail
from app.utils.email_sender import send_verification_email
from datetime import datetime
from werkzeug.utils import secure_filename
import uuid

settings_bp = Blueprint('account_settings', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@settings_bp.route('/account/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        action = request.form.get('action')

        # Update name (old template format)
        if 'full_name' in request.form and not action:
            name = request.form.get('full_name', '').strip()
            if name:
                current_user.full_name = name
                db.session.commit()
                flash('Name updated successfully.', 'success')
            else:
                flash('Name cannot be empty.', 'danger')

        # Remove photo (old template format)
        elif 'remove_photo' in request.form and not action:
            if current_user.profile_photo:
                upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
                old_path = os.path.join(upload_folder, current_user.profile_photo)
                if os.path.exists(old_path):
                    os.remove(old_path)
                current_user.profile_photo = None
                db.session.commit()
                flash('Profile photo removed.', 'success')

        # Upload photo (old template format)
        elif 'profile_photo' in request.files and not action:
            file = request.files['profile_photo']
            if file and file.filename and allowed_file(file.filename):
                ext = file.filename.rsplit('.', 1)[1].lower()
                filename = f"user_{current_user.id}_{uuid.uuid4().hex}.{ext}"
                upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
                os.makedirs(upload_folder, exist_ok=True)
                if current_user.profile_photo:
                    old_path = os.path.join(upload_folder, current_user.profile_photo)
                    if os.path.exists(old_path):
                        os.remove(old_path)
                file.save(os.path.join(upload_folder, filename))
                current_user.profile_photo = filename
                db.session.commit()
                flash('Profile photo updated.', 'success')

        # Add secondary email
        elif action == 'add_email':
            new_email = request.form.get('new_email', '').strip().lower()
            if not new_email:
                flash('Please enter an email address.', 'danger')
            elif new_email == current_user.email.lower():
                flash('This is already your primary email.', 'danger')
            elif UserEmail.query.filter_by(email=new_email).first():
                flash('This email is already linked to an account.', 'danger')
            else:
                user_email = UserEmail(user_id=current_user.id, email=new_email)
                user_email.generate_token()
                db.session.add(user_email)
                db.session.commit()
                verification_link = url_for(
                    'account_settings.verify_email',
                    token=user_email.verification_token,
                    _external=True
                )
                sent = send_verification_email(new_email, verification_link, current_user.full_name)
                if sent:
                    flash(f'Verification email sent to {new_email}. Please check your inbox.', 'success')
                else:
                    flash('Could not send verification email. Please try again.', 'danger')

        # Remove secondary email
        elif action == 'remove_email':
            email_id = request.form.get('email_id')
            user_email = UserEmail.query.filter_by(id=email_id, user_id=current_user.id).first()
            if user_email:
                db.session.delete(user_email)
                db.session.commit()
                flash('Email address removed.', 'success')

        return redirect(url_for('account_settings.settings'))

    secondary_emails = UserEmail.query.filter_by(user_id=current_user.id).all()
    return render_template('account/settings.html', secondary_emails=secondary_emails)


@settings_bp.route('/account/verify-email/<token>')
@login_required
def verify_email(token):
    user_email = UserEmail.query.filter_by(verification_token=token).first()
    if not user_email:
        flash('Invalid or expired verification link.', 'danger')
        return redirect(url_for('account_settings.settings'))

    if user_email.token_expiry < datetime.utcnow():
        db.session.delete(user_email)
        db.session.commit()
        flash('Verification link has expired. Please add the email again.', 'danger')
        return redirect(url_for('account_settings.settings'))

    user_email.is_verified = True
    user_email.verification_token = None
    user_email.token_expiry = None
    db.session.commit()
    flash('Email address verified successfully!', 'success')
    return redirect(url_for('account_settings.settings'))