from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models.recurring_transaction import RecurringTransaction
from app.models.transaction import Transaction
from app.models.account import Account
from app.models.category import Category
from datetime import datetime, timedelta
import calendar

recurring_bp = Blueprint('recurring', __name__)


def calculate_next_occurrence(current_date, frequency):
    if frequency == 'daily':
        return current_date + timedelta(days=1)
    elif frequency == 'weekly':
        return current_date + timedelta(weeks=1)
    elif frequency in ('monthly', 'every_3_months', 'every_6_months'):
        months_to_add = 1
        if frequency == 'every_3_months':
            months_to_add = 3
        elif frequency == 'every_6_months':
            months_to_add = 6
        month = current_date.month + months_to_add
        year = current_date.year
        while month > 12:
            month -= 12
            year += 1
        last_day = calendar.monthrange(year, month)[1]
        day = min(current_date.day, last_day)
        return current_date.replace(year=year, month=month, day=day)
    elif frequency == 'yearly':
        try:
            return current_date.replace(year=current_date.year + 1)
        except ValueError:
            return current_date.replace(year=current_date.year + 1, day=28)
    return current_date

def process_due_recurring(user_id):
    now = datetime.utcnow()
    recurring_list = RecurringTransaction.query.join(Account).filter(
        Account.user_id == user_id,
        RecurringTransaction.is_active == True,
        RecurringTransaction.next_occurrence_date <= now
    ).all()

    for rec in recurring_list:
        if rec.end_date and rec.end_date < now:
            rec.is_active = False
            db.session.commit()
            continue

        transaction = Transaction(
            account_id=rec.account_id,
            category_id=rec.category_id,
            recurring_transaction_id=rec.id,
            amount=rec.amount,
            transaction_type=rec.transaction_type,
            description=rec.description,
            transaction_date=rec.next_occurrence_date
        )

        account = Account.query.get(rec.account_id)
        if account:
            if rec.transaction_type == 'income':
                account.balance += rec.amount
            else:
                account.balance -= rec.amount

        rec.next_occurrence_date = calculate_next_occurrence(
            rec.next_occurrence_date, rec.frequency
        )
        db.session.add(transaction)

    db.session.commit()


@recurring_bp.route('/recurring', methods=['GET', 'POST'])
@login_required
def index():
    process_due_recurring(current_user.id)

    if request.method == 'POST':
        try:
            account_id = request.form.get('account_id')
            category_id = request.form.get('category_id') or None
            amount = float(request.form.get('amount'))
            transaction_type = request.form.get('transaction_type')
            description = request.form.get('description', '').strip()
            frequency = request.form.get('frequency')
            start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d')
            end_date_str = request.form.get('end_date')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d') if end_date_str else None

            rec = RecurringTransaction(
                account_id=account_id,
                category_id=category_id,
                amount=amount,
                transaction_type=transaction_type,
                description=description,
                frequency=frequency,
                start_date=start_date,
                next_occurrence_date=start_date,
                end_date=end_date,
                is_active=True
            )
            db.session.add(rec)
            db.session.commit()
            flash('Recurring transaction added successfully.', 'success')
        except Exception as e:
            flash(f'Error adding recurring transaction: {str(e)}', 'danger')

        return redirect(url_for('recurring.index'))

    accounts = Account.query.filter_by(user_id=current_user.id).all()
    categories = Category.query.filter_by(user_id=current_user.id).all()
    recurring_list = RecurringTransaction.query.join(Account).filter(
        Account.user_id == current_user.id
    ).order_by(RecurringTransaction.next_occurrence_date.asc()).all()

    return render_template(
        'recurring/index.html',
        accounts=accounts,
        categories=categories,
        recurring_list=recurring_list,
        now=datetime.utcnow()
    )


@recurring_bp.route('/recurring/<int:rec_id>/toggle', methods=['POST'])
@login_required
def toggle(rec_id):
    rec = RecurringTransaction.query.join(Account).filter(
        RecurringTransaction.id == rec_id,
        Account.user_id == current_user.id
    ).first_or_404()
    rec.is_active = not rec.is_active
    db.session.commit()
    status = 'resumed' if rec.is_active else 'paused'
    flash(f'Recurring transaction {status}.', 'success')
    return redirect(url_for('recurring.index'))


@recurring_bp.route('/recurring/<int:rec_id>/delete', methods=['POST'])
@login_required
def delete(rec_id):
    rec = RecurringTransaction.query.join(Account).filter(
        RecurringTransaction.id == rec_id,
        Account.user_id == current_user.id
    ).first_or_404()
    db.session.delete(rec)
    db.session.commit()
    flash('Recurring transaction deleted.', 'success')
    return redirect(url_for('recurring.index'))