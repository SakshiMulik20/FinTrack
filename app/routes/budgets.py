from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.models.budget import Budget
from app.models.transaction import Transaction
from app.models.account import Account
from app.models.category import Category
from datetime import datetime
from decimal import Decimal
from sqlalchemy import func

budgets_bp = Blueprint('budgets', __name__)

@budgets_bp.route('/budgets', methods=['GET', 'POST'])
@login_required
def index():
    now = datetime.utcnow()

    if request.method == 'POST':
        amount = Decimal(request.form.get('amount', '0'))
        category_id = request.form.get('category_id') or None

        existing = Budget.query.filter_by(
            user_id=current_user.id,
            month=now.month,
            year=now.year,
            category_id=category_id
        ).first()

        if existing:
            existing.amount_limit = amount
        else:
            db.session.add(Budget(
                user_id=current_user.id,
                amount_limit=amount,
                month=now.month,
                year=now.year,
                category_id=category_id
            ))
        db.session.commit()
        flash('Budget saved!', 'success')
        return redirect(url_for('budgets.index'))

    budgets = Budget.query.filter_by(
        user_id=current_user.id,
        month=now.month,
        year=now.year
    ).all()

    default_account = Account.query.filter_by(user_id=current_user.id, is_default=True).first()
    account_ids = [default_account.id] if default_account else []

    # Calculate spending per budget
    budget_data = []
    for budget in budgets:
        query = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.account_id.in_(account_ids),
            Transaction.transaction_type == 'expense',
            func.extract('month', Transaction.transaction_date) == now.month,
            func.extract('year', Transaction.transaction_date) == now.year
        )
        if budget.category_id:
            query = query.filter(Transaction.category_id == budget.category_id)
        spent = float(query.scalar() or 0)
        limit = float(budget.amount_limit)
        percent = min(round((spent / limit) * 100, 1), 100) if limit else 0
        budget_data.append({
            'budget': budget,
            'spent': spent,
            'percent': percent,
            'remaining': max(limit - spent, 0)
        })

    categories = Category.query.filter(
        (Category.user_id == current_user.id) | (Category.user_id == None)
    ).all()

    return render_template('budgets/index.html',
        budget_data=budget_data,
        categories=categories,
        now=now
    )

@budgets_bp.route('/budgets/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    budget = Budget.query.get_or_404(id)
    db.session.delete(budget)
    db.session.commit()
    flash('Budget removed.', 'success')
    return redirect(url_for('budgets.index'))