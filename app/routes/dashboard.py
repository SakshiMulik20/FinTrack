from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.budget import Budget
from app.models.category import Category
from app.utils.ml_predictor import predict_next_month
from app.utils.email_sender import send_expense_report
from datetime import datetime
from sqlalchemy import func

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.dashboard'))
    return render_template('landing.html')


@dashboard_bp.route('/dashboard')
@login_required
def dashboard():
    now = datetime.utcnow()
    accounts = Account.query.filter_by(user_id=current_user.id).all()

    default_account = Account.query.filter_by(user_id=current_user.id, is_default=True).first()
    if not default_account and accounts:
        default_account = accounts[0]

    selected_id = request.args.get('account_id', type=int)
    if selected_id:
        view_account = Account.query.filter_by(id=selected_id, user_id=current_user.id).first()
    else:
        view_account = default_account

    budget = Budget.query.filter_by(
        user_id=current_user.id, month=now.month, year=now.year, category_id=None
    ).first()

    total_spent = 0
    if default_account:
        result = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.account_id == default_account.id,
            Transaction.transaction_type == 'expense',
            func.extract('month', Transaction.transaction_date) == now.month,
            func.extract('year', Transaction.transaction_date) == now.year
        ).scalar()
        total_spent = float(result or 0)

    if budget:
        budget_limit = float(budget.amount_limit)
    elif default_account:
        budget_limit = total_spent + float(default_account.balance)
    else:
        budget_limit = 0

    budget_percent = 0
    if budget_limit > 0 and total_spent > 0:
        budget_percent = min(round((total_spent / budget_limit) * 100, 1), 100)

    recent_transactions = []
    category_spending = []
    if view_account:
        recent_transactions = Transaction.query.filter_by(
            account_id=view_account.id
        ).order_by(Transaction.transaction_date.desc()).limit(10).all()

        results = db.session.query(
            Category.name, func.sum(Transaction.amount)
        ).join(Transaction, Transaction.category_id == Category.id).filter(
            Transaction.account_id == view_account.id,
            Transaction.transaction_type == 'expense',
            func.extract('month', Transaction.transaction_date) == now.month,
            func.extract('year', Transaction.transaction_date) == now.year
        ).group_by(Category.name).all()
        category_spending = [{'name': r[0], 'amount': float(r[1])} for r in results]

    account_data = []
    for account in accounts:
        inc = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.account_id == account.id,
            Transaction.transaction_type == 'income'
        ).scalar() or 0
        exp = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.account_id == account.id,
            Transaction.transaction_type == 'expense'
        ).scalar() or 0
        account_data.append({
            'account': account,
            'income': float(inc),
            'expense': float(exp),
            'real_balance': float(account.balance)
        })

    prediction = None
    try:
        prediction = predict_next_month(current_user.id)
        if prediction and budget_limit > 0:
            prediction['savings'] = round(budget_limit - prediction['total_expense'], 2)
    except Exception as e:
        print(f"Prediction error: {e}")

    return render_template('dashboard/index.html',
        account_data=account_data,
        default_account=default_account,
        view_account=view_account,
        recent_transactions=recent_transactions,
        budget=budget,
        budget_limit=budget_limit,
        total_spent=total_spent,
        budget_percent=budget_percent,
        category_spending=category_spending,
        accounts=accounts,
        now=now,
        prediction=prediction
    )


@dashboard_bp.route('/dashboard/send-report', methods=['POST'])
@login_required
def send_report():
    try:
        prediction = predict_next_month(current_user.id)
        if prediction:
            sent = send_expense_report(
                to_email=current_user.email,
                user_name=current_user.full_name,
                prediction=prediction
            )
            if sent:
                flash('Detailed expense report sent to your email!', 'success')
            else:
                flash('Could not send report. Please try again.', 'danger')
        else:
            flash('Not enough data to generate a report yet.', 'warning')
    except Exception as e:
        flash('Something went wrong. Please try again.', 'danger')
        print(f"Report error: {e}")
    return redirect(url_for('dashboard.dashboard'))


@dashboard_bp.route('/accounts/set-default/<int:account_id>', methods=['POST'])
@login_required
def set_default(account_id):
    Account.query.filter_by(user_id=current_user.id).update({'is_default': False})
    account = Account.query.get_or_404(account_id)
    account.is_default = True
    db.session.commit()
    return redirect(url_for('dashboard.dashboard'))