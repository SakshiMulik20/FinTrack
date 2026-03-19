from datetime import datetime, timedelta
from app.extensions import db
from app.models.budget import Budget
from app.models.transaction import Transaction
from app.models.account import Account
from app.models.user import User
from app.models.category import Category
from app.utils.email_sender import send_budget_alert

# Cooldown: prevents duplicate alerts. Set to 1 for testing, 60 for production.
COOLDOWN_MINUTES = 1
_alert_cooldown = {}


def _get_user_name(user):
    return (getattr(user, 'name', None) or
            getattr(user, 'username', None) or
            getattr(user, 'first_name', None) or
            user.email)


def _get_spent(user_id, category_id, now):
    account_ids = [a.id for a in Account.query.filter_by(user_id=user_id).all()]
    if not account_ids:
        return 0.0
    spent = db.session.query(
        db.func.sum(Transaction.amount)
    ).filter(
        Transaction.account_id.in_(account_ids),
        Transaction.transaction_type == 'expense',
        Transaction.category_id == category_id,
        db.func.extract('month', Transaction.transaction_date) == now.month,
        db.func.extract('year', Transaction.transaction_date) == now.year
    ).scalar()
    return float(spent or 0.0)


def _send_alert_if_needed(user_id, budget, category_name, spent):
    if not budget.amount_limit or float(budget.amount_limit) <= 0:
        return

    percent = (spent / float(budget.amount_limit)) * 100

    if percent >= 100:
        alert_type = 'exceeded'
    elif percent >= 80:
        alert_type = 'warning'
    else:
        print(f"[BUDGET] {category_name}: {percent:.1f}% — below threshold")
        return

    cooldown_key = (user_id, budget.category_id, alert_type)
    last_sent = _alert_cooldown.get(cooldown_key)
    if last_sent and datetime.utcnow() - last_sent < timedelta(minutes=COOLDOWN_MINUTES):
        mins_ago = int((datetime.utcnow() - last_sent).seconds / 60)
        print(f"[BUDGET] Skipping — sent {mins_ago}min ago")
        return

    user = User.query.get(user_id)
    if not user or not user.email:
        return

    user_name = _get_user_name(user)
    result = send_budget_alert(
        user.email, user_name, category_name,
        spent, float(budget.amount_limit), percent, alert_type
    )

    if result:
        _alert_cooldown[cooldown_key] = datetime.utcnow()
        print(f"[BUDGET] {alert_type.upper()} alert sent → {user.email} | {category_name} | {percent:.1f}%")
    else:
        print(f"[BUDGET] Email FAILED — check .env credentials")

def check_budget_for_user(user_id, category_name):
    """Called immediately after an expense transaction is saved."""
    now = datetime.utcnow()

    # Try category-specific budget first
    category = Category.query.filter_by(name=category_name).first()
    if category:
        budget = Budget.query.filter_by(
            user_id=user_id,
            category_id=category.id
        ).first()

        if budget:
            spent = _get_spent(user_id, category.id, now)
            print(f"[BUDGET] Category budget — {category_name}: Rs.{spent:.0f} / Rs.{budget.amount_limit:.0f}")
            _send_alert_if_needed(user_id, budget, category_name, spent)
            return

    # Fallback: check total monthly budget (category_id is None)
    total_budget = Budget.query.filter_by(
        user_id=user_id,
        category_id=None
    ).first()

    if not total_budget:
        print(f"[BUDGET] No budget found for user_id={user_id}")
        return

    # Sum ALL expenses this month
    account_ids = [a.id for a in Account.query.filter_by(user_id=user_id).all()]
    total_spent = db.session.query(
        db.func.sum(Transaction.amount)
    ).filter(
        Transaction.account_id.in_(account_ids),
        Transaction.transaction_type == 'expense',
        db.func.extract('month', Transaction.transaction_date) == now.month,
        db.func.extract('year', Transaction.transaction_date) == now.year
    ).scalar()
    total_spent = float(total_spent or 0.0)

    print(f"[BUDGET] Total budget — spent=Rs.{total_spent:.0f}, limit=Rs.{total_budget.amount_limit:.0f}")
    _send_alert_if_needed(user_id, total_budget, 'Monthly Total', total_spent)

def check_all_budgets():
    """Periodic check — runs every hour via APScheduler."""
    now = datetime.utcnow()
    print(f"[BUDGET] Hourly check at {now.strftime('%H:%M')}")
    budgets = Budget.query.all()

    for budget in budgets:
        try:
            if budget.category_id:
                category = Category.query.get(budget.category_id)
                if not category:
                    continue
                spent = _get_spent(budget.user_id, budget.category_id, now)
                _send_alert_if_needed(budget.user_id, budget, category.name, spent)
            else:
                # Total monthly budget
                account_ids = [a.id for a in Account.query.filter_by(user_id=budget.user_id).all()]
                total_spent = db.session.query(
                    db.func.sum(Transaction.amount)
                ).filter(
                    Transaction.account_id.in_(account_ids),
                    Transaction.transaction_type == 'expense',
                    db.func.extract('month', Transaction.transaction_date) == now.month,
                    db.func.extract('year', Transaction.transaction_date) == now.year
                ).scalar()
                _send_alert_if_needed(budget.user_id, budget, 'Monthly Total', float(total_spent or 0.0))

        except Exception as e:
            print(f"[BUDGET] Error for budget {budget.id}: {e}")
            continue