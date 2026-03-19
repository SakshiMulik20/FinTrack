from app.extensions import db
from datetime import datetime

class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    recurring_transaction_id = db.Column(db.Integer, db.ForeignKey('recurring_transactions.id'), nullable=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    transaction_type = db.Column(db.String(10), nullable=False)  # 'income' or 'expense'
    description = db.Column(db.String(255))
    merchant_name = db.Column(db.String(100))
    transaction_date = db.Column(db.DateTime, default=datetime.utcnow)
    receipt_image_path = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Transaction {self.amount} {self.transaction_type}>'