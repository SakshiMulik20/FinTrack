from extensions import celery
from app.models.budget import Budget
from app.models.transaction import Transaction
from app.models.user import User
from app.utils.email_sender import send_budget_alert
from app import db
from datetime import datetime
from flask import current_app


@celery.task(name='app.tasks.budget_alerts.check_all_budgets')
def check_all_budgets():
    now = datetime.utcnow()
    budgets = Budget.query.all()

    for budget in budgets:
        try:
            spent = db.session.query(
                db.func.sum(Transaction.amount)
            ).filter(
                Transaction.user_id == budget.user_id,
                Transaction.type == 'expense',
                Transaction.category == budget.category,
                db.func.extract('month', Transaction.date) == now.month,
                db.func.extract('year', Transaction.date) == now.year
            ).scalar() or 0.0

            limit = budget.amount_limit
            if limit <= 0:
                continue

            percent = (spent / limit) * 100
            threshold = current_app.config.get('BUDGET_ALERT_THRESHOLD', 80)

            user = User.query.get(budget.user_id)
            if not user or not user.email:
                continue

            if percent >= 100:
                send_budget_alert(
                    to_email=user.email,
                    user_name=user.name,
                    category=budget.category,
                    spent=spent,
                    limit=limit,
                    percent=percent,
                    alert_type='exceeded'
                )
            elif percent >= threshold:
                send_budget_alert(
                    to_email=user.email,
                    user_name=user.name,
                    category=budget.category,
                    spent=spent,
                    limit=limit,
                    percent=percent,
                    alert_type='warning'
                )

        except Exception as e:
            print(f"Budget alert error for budget {budget.id}: {e}")
            continue

    return f"Checked {len(budgets)} budgets at {now}"


@celery.task(name='app.tasks.budget_alerts.check_user_budget_on_transaction')
def check_user_budget_on_transaction(user_id, category):
    """Call this after any expense transaction is added."""
    now = datetime.utcnow()

    budget = Budget.query.filter_by(
        user_id=user_id,
        category=category
    ).first()

    if not budget:
        return "No budget found"

    spent = db.session.query(
        db.func.sum(Transaction.amount)
    ).filter(
        Transaction.user_id == user_id,
        Transaction.type == 'expense',
        Transaction.category == category,
        db.func.extract('month', Transaction.date) == now.month,
        db.func.extract('year', Transaction.date) == now.year
    ).scalar() or 0.0

    limit = budget.amount_limit
    if limit <= 0:
        return "No limit set"

    percent = (spent / limit) * 100
    threshold = current_app.config.get('BUDGET_ALERT_THRESHOLD', 80)

    user = User.query.get(user_id)
    if not user or not user.email:
        return "No user email"

    if percent >= 100:
        send_budget_alert(user.email, user.name, category, spent, limit, percent, 'exceeded')
    elif percent >= threshold:
        send_budget_alert(user.email, user.name, category, spent, limit, percent, 'warning')

    return f"{category}: {percent:.1f}% used"