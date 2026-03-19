from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.models.savings_goal import SavingsGoal
from datetime import datetime
from decimal import Decimal

goals_bp = Blueprint('goals', __name__)

@goals_bp.route('/goals')
@login_required
def index():
    goals = SavingsGoal.query.filter_by(user_id=current_user.id).order_by(SavingsGoal.created_at.desc()).all()
    goal_data = []
    for goal in goals:
        target = float(goal.target_amount)
        current = float(goal.current_amount)
        percent = min(round((current / target) * 100, 1), 100) if target else 0
        goal_data.append({'goal': goal, 'percent': percent})
    return render_template('goals/index.html', goal_data=goal_data)

@goals_bp.route('/goals/add', methods=['GET', 'POST'])
@login_required
def add():
    if request.method == 'POST':
        name = request.form.get('name')
        target_amount = Decimal(request.form.get('target_amount', '0'))
        description = request.form.get('description')
        target_date = request.form.get('target_date')
        target_date = datetime.strptime(target_date, '%Y-%m-%d') if target_date else None

        goal = SavingsGoal(
            user_id=current_user.id,
            name=name,
            target_amount=target_amount,
            current_amount=Decimal('0'),
            description=description,
            target_date=target_date
        )
        db.session.add(goal)
        db.session.commit()
        flash('Savings goal created!', 'success')
        return redirect(url_for('goals.index'))
    return render_template('goals/add.html')

@goals_bp.route('/goals/deposit/<int:id>', methods=['POST'])
@login_required
def deposit(id):
    goal = SavingsGoal.query.get_or_404(id)
    amount = Decimal(request.form.get('amount', '0'))
    goal.current_amount += amount
    if goal.current_amount >= goal.target_amount:
        goal.is_completed = True
        flash(f'Congratulations! You reached your goal: {goal.name}!', 'success')
    else:
        flash(f'₹{amount} added to {goal.name}!', 'success')
    db.session.commit()
    return redirect(url_for('goals.index'))

@goals_bp.route('/goals/delete/<int:id>', methods=['POST'])
@login_required
def delete(id):
    goal = SavingsGoal.query.get_or_404(id)
    db.session.delete(goal)
    db.session.commit()
    flash('Goal deleted.', 'success')
    return redirect(url_for('goals.index'))