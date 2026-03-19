import os
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

from flask import Blueprint, redirect, url_for, flash
from flask_dance.contrib.google import make_google_blueprint, google
from flask_dance.consumer import oauth_authorized
from flask_login import login_user
from app.extensions import db
from app.models.user import User
from app.models.account import Account

google_auth_bp = Blueprint('google_auth', __name__)

google_bp = make_google_blueprint(
    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
    scope=["openid", "https://www.googleapis.com/auth/userinfo.email",
           "https://www.googleapis.com/auth/userinfo.profile"]
)

@oauth_authorized.connect_via(google_bp)
def google_logged_in(blueprint, token):
    if not token:
        flash('Google login failed.', 'error')
        return False

    resp = blueprint.session.get('/oauth2/v2/userinfo')
    if not resp.ok:
        flash('Could not get your Google info.', 'error')
        return False

    google_info = resp.json()
    email = google_info.get('email')
    full_name = google_info.get('name', email)

    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(full_name=full_name, email=email)
        user.set_password(os.urandom(24).hex())
        db.session.add(user)
        db.session.flush()

        default_account = Account(
            user_id=user.id,
            name='Personal',
            account_type='Current Account',
            balance=0.00,
            is_default=True
        )
        db.session.add(default_account)
        db.session.commit()

    login_user(user)
    return False