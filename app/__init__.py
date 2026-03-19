import os
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

from flask import Flask
from .config import config
from .extensions import db, migrate, login_manager, mail, limiter


def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    limiter.init_app(app)

       # APScheduler — hourly budget check, runs inside Flask, no Redis needed
    from apscheduler.schedulers.background import BackgroundScheduler
    scheduler = BackgroundScheduler(timezone='Asia/Kolkata')
    def scheduled_budget_check():
        with app.app_context():
            from app.utils.budget_checker import check_all_budgets
            check_all_budgets()
    scheduler.add_job(scheduled_budget_check, 'interval', hours=1)
    scheduler.start()
    
    from . import models

    from .routes.auth import auth_bp
    from .routes.dashboard import dashboard_bp
    from .routes.google_auth import google_auth_bp, google_bp
    from .routes.transactions import transactions_bp
    from .routes.budgets import budgets_bp
    from .routes.goals import goals_bp
    from .routes.analytics import analytics_bp
    from .routes.account_settings import settings_bp
    from .routes.accounts import accounts_bp
    from .routes.recurring import recurring_bp
    from app.routes.receipts import receipts_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(google_auth_bp)
    app.register_blueprint(google_bp, url_prefix='/login')
    app.register_blueprint(transactions_bp)
    app.register_blueprint(budgets_bp)
    app.register_blueprint(goals_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(accounts_bp)
    app.register_blueprint(recurring_bp)
    app.register_blueprint(receipts_bp)

    return app