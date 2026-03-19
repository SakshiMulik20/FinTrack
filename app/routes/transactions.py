from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.models.transaction import Transaction
from app.models.account import Account
from app.models.category import Category
from datetime import datetime
from decimal import Decimal
from app.utils.budget_checker import check_budget_for_user

transactions_bp = Blueprint('transactions', __name__)

@transactions_bp.route('/transactions')
@login_required
def index():
    accounts = Account.query.filter_by(user_id=current_user.id).all()
    account_id = request.args.get('account_id')
    search = request.args.get('search', '')

    if account_id:
        query = Transaction.query.filter_by(account_id=account_id)
    else:
        account_ids = [a.id for a in accounts]
        query = Transaction.query.filter(Transaction.account_id.in_(account_ids))

    if search:
        query = query.filter(Transaction.description.ilike(f'%{search}%'))

    transactions = query.order_by(Transaction.transaction_date.desc()).all()

    return render_template('transactions/index.html',
        transactions=transactions,
        accounts=accounts,
        search=search,
        selected_account=account_id
    )

@transactions_bp.route('/transactions/add', methods=['GET', 'POST'])
@login_required
def add():
    accounts = Account.query.filter_by(user_id=current_user.id).all()
    categories = Category.query.filter(
        (Category.user_id == current_user.id) | (Category.user_id == None)
    ).all()

    if request.method == 'POST':
        account_id = request.form.get('account_id')
        category_id = request.form.get('category_id') or None
        amount = Decimal(request.form.get('amount', '0'))
        transaction_type = request.form.get('transaction_type')
        description = request.form.get('description')
        transaction_date = datetime.strptime(request.form.get('transaction_date'), '%Y-%m-%d')

        transaction = Transaction(
            account_id=account_id,
            category_id=category_id,
            amount=amount,
            transaction_type=transaction_type,
            description=description,
            transaction_date=transaction_date
        )
        db.session.add(transaction)

        # Update account balance
        account = Account.query.get(account_id)
        if transaction_type == 'income':
            account.balance += amount
        else:
            account.balance -= amount

        db.session.commit()
                # Trigger budget alert check if it's an expense
        if transaction_type == 'expense' and category_id:
            category = Category.query.get(category_id)
            if category:
                check_budget_for_user(current_user.id, category.name)
        flash('Transaction added successfully!', 'success')
        return redirect(url_for('transactions.index', account_id=account_id))

    return render_template('transactions/add.html',
        accounts=accounts,
        categories=categories,
        today=datetime.utcnow().strftime('%Y-%m-%d')
    )

@transactions_bp.route('/transactions/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    transaction = Transaction.query.get_or_404(id)
    account = Account.query.get(transaction.account_id)

    # Reverse the balance change
    if transaction.transaction_type == 'income':
        account.balance -= transaction.amount
    else:
        account.balance += transaction.amount

    db.session.delete(transaction)
    db.session.commit()
    flash('Transaction deleted.', 'success')
    return redirect(url_for('transactions.index', account_id=transaction.account_id))