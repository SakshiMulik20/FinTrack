import os
import smtplib
import uuid
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def _send_gmail(to_email, subject, html_content, plain_content=None):
    sender = os.environ.get('MAIL_FROM')
    password = os.environ.get('GMAIL_APP_PASSWORD')

    if not sender or not password:
        print("Email error: MAIL_FROM or GMAIL_APP_PASSWORD not set in .env")
        return False

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = f'FinTrack <{sender}>'
    msg['To'] = to_email
    msg['Message-ID'] = f'<{uuid.uuid4()}@fintrack.app>'
    msg['Date'] = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')
    msg['X-Mailer'] = 'FinTrack Mailer'

    plain = plain_content or 'Please view this email in an HTML-compatible client.'
    msg.attach(MIMEText(plain, 'plain', 'utf-8'))
    msg.attach(MIMEText(html_content, 'html', 'utf-8'))

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.ehlo()
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Email send error: {e}")
        return False


def send_verification_email(to_email, verification_link, user_name):
    html = f"""
    <div style="font-family:Arial,sans-serif; max-width:600px; margin:0 auto;">
        <h2 style="color:#0f2942;">FinTrack Email Verification</h2>
        <p>Hi {user_name},</p>
        <p>Please verify your email address by clicking the link below:</p>
        <a href='{verification_link}' style="background:linear-gradient(135deg,#15304f,#0891b2); color:white; padding:12px 24px;
           text-decoration:none; border-radius:8px; display:inline-block; font-weight:600;">
           Verify Email Address
        </a>
        <p style="color:#888; margin-top:16px;">This link expires in 24 hours.</p>
    </div>
    """
    plain = f"Hi {user_name},\n\nVerify your FinTrack email here:\n{verification_link}\n\nThis link expires in 24 hours."
    return _send_gmail(to_email, "Verify your email address - FinTrack", html, plain)


def send_expense_report(to_email, user_name, prediction):
    next_month = prediction['next_month']
    total = prediction['total_expense']
    savings = prediction['savings']
    categories = prediction['categories']

    category_rows = ''
    for cat, amount in categories:
        category_rows += f'''
        <tr>
            <td style="padding:8px 16px; border-bottom:1px solid #f0f0f0;">{cat}</td>
            <td style="padding:8px 16px; border-bottom:1px solid #f0f0f0; text-align:right; color:#b91c1c;">Rs.{amount:,.2f}</td>
        </tr>'''

    savings_color = '#047857' if savings >= 0 else '#b91c1c'
    savings_label = 'Estimated Savings' if savings >= 0 else 'Estimated Deficit'

    html = f'''
    <div style="font-family:Arial,sans-serif; max-width:600px; margin:0 auto; background:#f8f9fa; padding:20px;">
        <div style="background:linear-gradient(135deg,#15304f,#0891b2); padding:24px; border-radius:12px 12px 0 0; text-align:center;">
            <h2 style="color:white; margin:0;">FinTrack Expense Report</h2>
            <p style="color:#cffafe; margin:8px 0 0;">{next_month} Prediction</p>
        </div>
        <div style="background:white; padding:24px; border-radius:0 0 12px 12px;">
            <p style="color:#555;">Hi {user_name},</p>
            <p style="color:#555;">Based on your spending history, here is your predicted expense breakdown for <strong>{next_month}</strong>:</p>
            <div style="background:#fff3cd; border-radius:8px; padding:16px; text-align:center; margin:16px 0;">
                <p style="margin:0; color:#856404; font-size:0.9rem;">Total Predicted Expenses</p>
                <h2 style="margin:8px 0 0; color:#b91c1c;">Rs.{total:,.2f}</h2>
            </div>
            <h4 style="color:#333; margin-top:24px;">Breakdown by Category</h4>
            <table style="width:100%; border-collapse:collapse; margin-top:8px;">
                <thead>
                    <tr style="background:#f0fafd;">
                        <th style="padding:8px 16px; text-align:left; color:#888; font-size:0.8rem;">CATEGORY</th>
                        <th style="padding:8px 16px; text-align:right; color:#888; font-size:0.8rem;">PREDICTED AMOUNT</th>
                    </tr>
                </thead>
                <tbody>{category_rows}</tbody>
            </table>
            <div style="background:#f0fdf4; border-radius:8px; padding:16px; text-align:center; margin:24px 0 8px;">
                <p style="margin:0; color:#555; font-size:0.9rem;">{savings_label}</p>
                <h2 style="margin:8px 0 0; color:{savings_color};">Rs.{abs(savings):,.2f}</h2>
            </div>
            <p style="color:#999; font-size:0.8rem; text-align:center; margin-top:24px;">
                This is an AI-based prediction using your past transactions. Actual amounts may vary.
            </p>
            <hr style="border:none; border-top:1px solid #eee;">
            <p style="color:#bbb; font-size:0.75rem; text-align:center;">FinTrack &mdash; Personal Finance Tracker</p>
        </div>
    </div>
    '''

    plain = f"""FinTrack Expense Report - {next_month}

Hi {user_name},

Your predicted expenses for {next_month}: Rs.{total:,.2f}

{savings_label}: Rs.{abs(savings):,.2f}

Category Breakdown:
""" + '\n'.join([f"  {cat}: Rs.{amt:,.2f}" for cat, amt in categories[:8]]) + """

This is an AI-based prediction. Actual amounts may vary.
-- FinTrack Personal Finance Tracker
"""

    return _send_gmail(
        to_email,
        f'FinTrack - Your Expense Prediction for {next_month}',
        html,
        plain
    )


def send_budget_alert(to_email, user_name, category, spent, limit, percent, alert_type):
    if alert_type == 'exceeded':
        subject = f'FinTrack - Budget Exceeded: {category}'
        color = '#b91c1c'
        headline = 'Budget Limit Exceeded!'
        message = f'You have exceeded your <strong>{category}</strong> budget for this month.'
    else:
        subject = f'FinTrack - Budget Warning: {category}'
        color = '#f39c12'
        headline = 'Budget Warning'
        message = f'You are nearing your <strong>{category}</strong> budget limit for this month.'

    remaining = max(0, limit - spent)
    display_percent = min(percent, 100.0)
    bar_width = int(display_percent)

    html = f'''
    <div style="font-family:Arial,sans-serif; max-width:600px; margin:0 auto; background:#f8f9fa; padding:20px;">
        <div style="background:{color}; padding:24px; border-radius:12px 12px 0 0; text-align:center;">
            <h2 style="color:white; margin:0;">&#9888; {headline}</h2>
        </div>
        <div style="background:white; padding:24px; border-radius:0 0 12px 12px;">
            <p style="color:#555;">Hi {user_name},</p>
            <p style="color:#555;">{message}</p>

            <div style="background:#f8f9fa; border-radius:8px; padding:16px; margin:16px 0;">
                <table style="width:100%; border-collapse:collapse;">
                    <tr><td style="padding:6px 0; color:#888;">Category</td><td style="padding:6px 0; text-align:right; font-weight:bold; color:#333;">{category}</td></tr>
                    <tr><td style="padding:6px 0; color:#888;">Budget Limit</td><td style="padding:6px 0; text-align:right; color:#333;">Rs.{limit:,.2f}</td></tr>
                    <tr><td style="padding:6px 0; color:#888;">Amount Spent</td><td style="padding:6px 0; text-align:right; font-weight:bold; color:{color};">Rs.{spent:,.2f}</td></tr>
                    <tr><td style="padding:6px 0; color:#888;">Remaining</td><td style="padding:6px 0; text-align:right; color:#047857;">Rs.{remaining:,.2f}</td></tr>
                </table>
            </div>

            <div style="background:#eee; border-radius:999px; height:14px; margin:16px 0;">
                <div style="background:{color}; width:{bar_width}%; height:14px; border-radius:999px;"></div>
            </div>
            <p style="text-align:center; color:{color}; font-weight:bold; margin:0;">{display_percent:.0f}% of budget used</p>

            <p style="color:#999; font-size:0.8rem; text-align:center; margin-top:24px;">
                Log in to FinTrack to review your spending and adjust your budget.
            </p>
            <hr style="border:none; border-top:1px solid #eee;">
            <p style="color:#bbb; font-size:0.75rem; text-align:center;">FinTrack &mdash; Personal Finance Tracker</p>
        </div>
    </div>
    '''

    plain = f"""FinTrack Budget Alert - {category}

Hi {user_name},

{'Budget Exceeded!' if alert_type == 'exceeded' else 'Budget Warning'}

Category   : {category}
Limit      : Rs.{limit:,.2f}
Spent      : Rs.{spent:,.2f}
Remaining  : Rs.{remaining:,.2f}
Usage      : {percent:.1f}%

Log in to FinTrack to review your spending and adjust your budget.
-- FinTrack Personal Finance Tracker
"""

    return _send_gmail(to_email, subject, html, plain)