from datetime import datetime


def load_user_transactions(user_id):
    from app.models.transaction import Transaction
    from app.models.account import Account
    from app.models.category import Category
    from app import db

    results = db.session.query(
        Transaction.amount,
        Transaction.transaction_type,
        Transaction.transaction_date,
        Category.name
    ).join(Account, Transaction.account_id == Account.id)\
     .outerjoin(Category, Transaction.category_id == Category.id)\
     .filter(Account.user_id == user_id).all()

    if not results:
        return []

    rows = []
    for r in results:
        rows.append({
            'month_num': r.transaction_date.year * 12 + r.transaction_date.month,
            'amount': float(r.amount),
            'category': r.name or 'Other',
            'type': r.transaction_type
        })
    return rows


def predict_next_month(user_id):
    transactions = load_user_transactions(user_id)

    now = datetime.utcnow()
    next_month_date = datetime(
        now.year if now.month < 12 else now.year + 1,
        now.month % 12 + 1, 1
    )

    expenses = [t for t in transactions if t['type'] == 'expense']

    if not expenses:
        return None

    monthly_totals = {}
    monthly_categories = {}

    for t in expenses:
        m = t['month_num']
        monthly_totals[m] = monthly_totals.get(m, 0) + t['amount']
        if m not in monthly_categories:
            monthly_categories[m] = {}
        cat = t['category']
        monthly_categories[m][cat] = monthly_categories[m].get(cat, 0) + t['amount']

    sorted_months = sorted(monthly_totals.keys())
    num_months = len(sorted_months)

    if num_months == 0:
        return None
    elif num_months == 1:
        total_prediction = monthly_totals[sorted_months[0]]
        confidence = 'low'
    elif num_months == 2:
        total_prediction = sum(monthly_totals[m] for m in sorted_months) / 2
        confidence = 'medium'
    else:
        weights = list(range(1, num_months + 1))
        weighted_sum = sum(
            monthly_totals[sorted_months[i]] * weights[i]
            for i in range(num_months)
        )
        total_prediction = weighted_sum / sum(weights)
        confidence = 'high'

    all_categories = set()
    for cats in monthly_categories.values():
        all_categories.update(cats.keys())

    category_predictions = {}
    for cat in all_categories:
        values = []
        weights_list = []
        for i, m in enumerate(sorted_months):
            if cat in monthly_categories[m]:
                values.append(monthly_categories[m][cat])
                weights_list.append(i + 1)
        if values:
            weighted = sum(v * w for v, w in zip(values, weights_list))
            category_predictions[cat] = round(weighted / sum(weights_list), 2)

    cat_total = sum(category_predictions.values())
    if cat_total > 0 and abs(cat_total - total_prediction) > 1:
        scale = total_prediction / cat_total
        category_predictions = {k: round(v * scale, 2) for k, v in category_predictions.items()}

    sorted_categories = sorted(category_predictions.items(), key=lambda x: x[1], reverse=True)

    return {
        'total_expense': round(total_prediction, 2),
        'income': 0,
        'savings': 0,
        'categories': sorted_categories,
        'next_month': next_month_date.strftime('%B %Y'),
        'confidence': confidence,
        'months_of_data': num_months
    }