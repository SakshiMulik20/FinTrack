from flask import Blueprint, render_template, request, flash
from flask_login import login_required, current_user
from app.models.account import Account
from app.models.category import Category
from app.utils.ocr_reader import extract_amount_from_receipt
from datetime import datetime

receipts_bp = Blueprint('receipts', __name__)


@receipts_bp.route('/receipts/scan', methods=['GET', 'POST'])
@login_required
def scan():
    accounts = Account.query.filter_by(user_id=current_user.id).all()
    categories = Category.query.filter(
        (Category.user_id == current_user.id) | (Category.user_id == None)
    ).all()

    extracted_amount = None
    raw_text = None

    if request.method == 'POST' and 'receipt' in request.files:
        file = request.files['receipt']
        if file and file.filename:
            extracted_amount, raw_text = extract_amount_from_receipt(file)
            if not extracted_amount:
                flash('Could not detect an amount. Please enter it manually.', 'warning')

    return render_template('receipts/scan.html',
        accounts=accounts,
        categories=categories,
        extracted_amount=extracted_amount,
        today=datetime.utcnow().strftime('%Y-%m-%d')
    )