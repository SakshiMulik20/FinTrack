from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.models.account import Account
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