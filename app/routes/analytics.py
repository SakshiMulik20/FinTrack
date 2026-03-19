from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models.transaction import Transaction
from app.models.account import Account
from app.models.category import Category
from datetime import datetime, timedelta
from sqlalchemy import func

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/analytics')
@login_required
def index():
    return render_template('analytics/index.html')

@analytics_bp.route('/analytics/data')
@login_required
def data():
    view = request.args.get('view', 'monthly')
    accounts = Account.query.filter_by(user_id=current_user.id).all()
    account_ids = [a.id for a in accounts]
    now = datetime.utcnow()

    labels, income_data, expense_data = [], [], []

    if view == 'daily':
        for i in range(23, -1, -1):
            label = f"{i}:00" if i % 3 == 0 else ""
            labels.append(f"{i}:00")
            inc = db.session.query(func.sum(Transaction.amount)).filter(
                Transaction.account_id.in_(account_ids),
                Transaction.transaction_type == 'income',
                func.date(Transaction.transaction_date) == now.date(),
                func.extract('hour', Transaction.transaction_date) == i
            ).scalar() or 0
            exp = db.session.query(func.sum(Transaction.amount)).filter(
                Transaction.account_id.in_(account_ids),
                Transaction.transaction_type == 'expense',
                func.date(Transaction.transaction_date) == now.date(),
                func.extract('hour', Transaction.transaction_date) == i
            ).scalar() or 0
            income_data.append(float(inc))
            expense_data.append(float(exp))

    elif view == 'weekly':
        for i in range(6, -1, -1):
            day = now - timedelta(days=i)
            labels.append(day.strftime('%a %d'))
            inc = db.session.query(func.sum(Transaction.amount)).filter(
                Transaction.account_id.in_(account_ids),
                Transaction.transaction_type == 'income',
                func.date(Transaction.transaction_date) == day.date()
            ).scalar() or 0
            exp = db.session.query(func.sum(Transaction.amount)).filter(
                Transaction.account_id.in_(account_ids),
                Transaction.transaction_type == 'expense',
                func.date(Transaction.transaction_date) == day.date()
            ).scalar() or 0
            income_data.append(float(inc))
            expense_data.append(float(exp))

    elif view == 'monthly':
        for i in range(29, -1, -1):
            day = now - timedelta(days=i)
            labels.append(day.strftime('%d %b'))
            inc = db.session.query(func.sum(Transaction.amount)).filter(
                Transaction.account_id.in_(account_ids),
                Transaction.transaction_type == 'income',
                func.date(Transaction.transaction_date) == day.date()
            ).scalar() or 0
            exp = db.session.query(func.sum(Transaction.amount)).filter(
                Transaction.account_id.in_(account_ids),
                Transaction.transaction_type == 'expense',
                func.date(Transaction.transaction_date) == day.date()
            ).scalar() or 0
            income_data.append(float(inc))
            expense_data.append(float(exp))

    elif view == '6month':
        for i in range(5, -1, -1):
            month_date = datetime(now.year, now.month, 1) - timedelta(days=i * 30)
            labels.append(month_date.strftime('%b %Y'))
            inc = db.session.query(func.sum(Transaction.amount)).filter(
                Transaction.account_id.in_(account_ids),
                Transaction.transaction_type == 'income',
                func.extract('month', Transaction.transaction_date) == month_date.month,
                func.extract('year', Transaction.transaction_date) == month_date.year
            ).scalar() or 0
            exp = db.session.query(func.sum(Transaction.amount)).filter(
                Transaction.account_id.in_(account_ids),
                Transaction.transaction_type == 'expense',
                func.extract('month', Transaction.transaction_date) == month_date.month,
                func.extract('year', Transaction.transaction_date) == month_date.year
            ).scalar() or 0
            income_data.append(float(inc))
            expense_data.append(float(exp))

    elif view == 'yearly':
        for i in range(11, -1, -1):
            month_date = datetime(now.year, now.month, 1) - timedelta(days=i * 30)
            labels.append(month_date.strftime('%b %Y'))
            inc = db.session.query(func.sum(Transaction.amount)).filter(
                Transaction.account_id.in_(account_ids),
                Transaction.transaction_type == 'income',
                func.extract('month', Transaction.transaction_date) == month_date.month,
                func.extract('year', Transaction.transaction_date) == month_date.year
            ).scalar() or 0
            exp = db.session.query(func.sum(Transaction.amount)).filter(
                Transaction.account_id.in_(account_ids),
                Transaction.transaction_type == 'expense',
                func.extract('month', Transaction.transaction_date) == month_date.month,
                func.extract('year', Transaction.transaction_date) == month_date.year
            ).scalar() or 0
            income_data.append(float(inc))
            expense_data.append(float(exp))

    category_results = db.session.query(
        Category.name, Category.color_hex, func.sum(Transaction.amount)
    ).join(Transaction, Transaction.category_id == Category.id).filter(
        Transaction.account_id.in_(account_ids),
        Transaction.transaction_type == 'expense',
        func.extract('month', Transaction.transaction_date) == now.month,
        func.extract('year', Transaction.transaction_date) == now.year
    ).group_by(Category.name, Category.color_hex).all()

    return jsonify({
        'labels': labels,
        'income': income_data,
        'expenses': expense_data,
        'categories': [{'name': r[0], 'color': r[1], 'amount': float(r[2])} for r in category_results]
    })