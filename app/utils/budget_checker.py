from datetime import datetime, timedelta
from app.extensions import db
from app.models.budget import Budget
from app.models.transaction import Transaction
from app.models.account import Account
from app.models.user import User
from app.utils.email_sender import send_budget_alert

# Cooldown: prevents duplicate alerts. Set to 1 for testing, 60 for production.
COOLDOWN_MINUTES = 1
_alert_cooldown = {}


def _get_user_name(user):
    return (getattr(user, 'full_name', None) or
            getattr(user, 'name', None) or
            getattr(user, 'username', None) or
            getattr(user, 'first_name', None) or
            user.email)


def _get_default_account_id(user_id):
    acc = Account.query.filter_by(user_id=user_id, is_default=True).first()
    return acc.id if acc else None


def _get_total_spent(user_id, now):
    """Sum ALL expenses this month, only from the default (active) account."""
    account_id = _get_default_account_id(user_id)
    if not account_id:
        return 0.0
    total = db.session.query(
        db.func.sum(Transaction.amount)
    ).filter(
        Transaction.account_id == account_id,
        Transaction.transaction_type == 'expense',
        db.func.extract('month', Transaction.transaction_date) == now.month,
        db.func.extract('year', Transaction.transaction_date) == now.year
    ).scalar()
    return float(total or 0.0)


def _send_alert_if_needed(user_id, budget, spent):
    if not budget.amount_limit or float(budget.amount_limit) <= 0:
        return

    percent = (spent / float(budget.amount_limit)) * 100

    if percent >= 100:
        alert_type = 'exceeded'
    elif percent >= 80:
        alert_type = 'warning'
    else:
        print(f"[BUDGET] Monthly Total: {percent:.1f}% — below threshold")
        return

    cooldown_key = (user_id, alert_type)
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
        user.email, user_name, 'Monthly Total',
        spent, float(budget.amount_limit), percent, alert_type
    )

    if result:
        _alert_cooldown[cooldown_key] = datetime.utcnow()
        print(f"[BUDGET] {alert_type.upper()} alert sent → {user.email} | {percent:.1f}%")
    else:
        print(f"[BUDGET] Email FAILED — check .env credentials")


def check_budget_for_user(user_id, category_name=None):
    """Called immediately after an expense transaction is saved.
    Only checks the Monthly Total budget against the default account's spending."""
    now = datetime.utcnow()

    total_budget = Budget.query.filter_by(
        user_id=user_id,
        category_id=None,
        month=now.month,
        year=now.year
    ).first()

    if not total_budget:
        print(f"[BUDGET] No Monthly Total budget set for user_id={user_id}")
        return

    total_spent = _get_total_spent(user_id, now)
    print(f"[BUDGET] Monthly Total (default account) — spent=₹{total_spent:.0f}, limit=₹{total_budget.amount_limit:.0f}")
    _send_alert_if_needed(user_id, total_budget, total_spent)


def check_all_budgets():
    """Periodic check — runs every hour via APScheduler.
    Only checks each user's Monthly Total budget."""
    now = datetime.utcnow()
    print(f"[BUDGET] Hourly check at {now.strftime('%H:%M')}")

    total_budgets = Budget.query.filter_by(
        category_id=None,
        month=now.month,
        year=now.year
    ).all()

    for budget in total_budgets:
        try:
            total_spent = _get_total_spent(budget.user_id, now)
            _send_alert_if_needed(budget.user_id, budget, total_spent)
        except Exception as e:
            print(f"[BUDGET] Error for budget {budget.id}: {e}")
            continue