from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.recurring_transaction import RecurringTransaction
from app.models.budget import Budget
from decimal import Decimal

accounts_bp = Blueprint('accounts', __name__)


@accounts_bp.route('/accounts/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        name = request.form.get('name')
        account_type = request.form.get('account_type')
        balance = Decimal(request.form.get('balance', '0'))

        existing_default = Account.query.filter_by(user_id=current_user.id, is_default=True).first()
        is_default = not existing_default

        account = Account(
            user_id=current_user.id,
            name=name,
            account_type=account_type,
            balance=balance,
            is_default=is_default
        )
        db.session.add(account)
        db.session.commit()
        flash(f'Account "{name}" created successfully!', 'success')
        return redirect(url_for('dashboard.dashboard'))

    return render_template('accounts/add.html')


@accounts_bp.route('/accounts/delete/<int:account_id>', methods=['POST'])
@login_required
def delete(account_id):
    account = Account.query.filter_by(id=account_id, user_id=current_user.id).first_or_404()

    account_name = account.name
    was_default = account.is_default

    try:
        # Delete linked transactions
        Transaction.query.filter_by(account_id=account.id).delete(synchronize_session=False)

        # Delete linked recurring transactions
        RecurringTransaction.query.filter_by(account_id=account.id).delete(synchronize_session=False)

        # Delete linked budgets (only if your Budget model is account-scoped)
        if hasattr(Budget, 'account_id'):
            Budget.query.filter_by(account_id=account.id).delete(synchronize_session=False)

        db.session.delete(account)

        # If we just deleted the default account, promote another one
        if was_default:
            next_default = Account.query.filter_by(user_id=current_user.id).first()
            if next_default:
                next_default.is_default = True

        db.session.commit()
        flash(f'Account "{account_name}" and its related data were deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Could not delete account: {str(e)}', 'error')

    return redirect(url_for('dashboard.dashboard'))