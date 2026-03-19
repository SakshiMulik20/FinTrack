from app.extensions import db
from datetime import datetime

class Account(db.Model):
    __tablename__ = 'accounts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    balance = db.Column(db.Numeric(10, 2), default=0.00)
    account_type = db.Column(db.String(50), default='Current Account')
    currency = db.Column(db.String(10), default='USD')
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    transactions = db.relationship('Transaction', backref='account', lazy=True)
    recurring_transactions = db.relationship('RecurringTransaction', backref='account', lazy=True)

    def __repr__(self):
        return f'<Account {self.name}>'