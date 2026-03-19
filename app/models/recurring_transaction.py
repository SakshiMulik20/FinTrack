from app.extensions import db
from datetime import datetime

class RecurringTransaction(db.Model):
    __tablename__ = 'recurring_transactions'

    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    transaction_type = db.Column(db.String(10), nullable=False)
    description = db.Column(db.String(255))
    frequency = db.Column(db.String(20), nullable=False)  # daily, weekly, monthly, yearly
    start_date = db.Column(db.DateTime, nullable=False)
    next_occurrence_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    transactions = db.relationship('Transaction', backref='recurring_source', lazy=True)

    def __repr__(self):
        return f'<RecurringTransaction {self.description}>'