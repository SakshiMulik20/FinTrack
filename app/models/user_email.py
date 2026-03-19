from app import db
from datetime import datetime
import secrets

class UserEmail(db.Model):
    __tablename__ = 'user_emails'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    is_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(100), nullable=True)
    token_expiry = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='secondary_emails')

    def generate_token(self):
        self.verification_token = secrets.token_urlsafe(32)
        from datetime import timedelta
        self.token_expiry = datetime.utcnow() + timedelta(hours=24)