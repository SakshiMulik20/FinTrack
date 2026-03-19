from app import create_app
from app.extensions import db
from app.models.account import Account

app = create_app()
with app.app_context():
    account = Account.query.filter_by(name='Personal').first()
    if account:
        account.balance = 15000 - 140  # opening balance minus expenses already made
        db.session.commit()
        print(f"Fixed! Balance is now: {account.balance}")
    else:
        print("Account not found")