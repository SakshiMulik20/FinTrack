import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def _send_gmail(to_email, subject, html_content):
    sender = os.environ.get('MAIL_FROM')
    password = os.environ.get('GMAIL_APP_PASSWORD')

    if not sender or not password:
        print("Email error: MAIL_FROM or GMAIL_APP_PASSWORD not set in .env")
        return False

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = f'FinTrack <{sender}>'
    msg['To'] = to_email
    msg.attach(MIMEText(html_content, 'html'))

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.ehlo()
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"Email send error: {e}")
        return False


def send_verification_email(to_email, verification_link, user_name):
    html = f"""
    <div style="font-family:Arial,sans-serif; max-width:600px; margin:0 auto;">
        <h2>FinTrack Email Verification</h2>
        <p>Hi {user_name},</p>
        <p>Please verify your email address {to_email} by clicking the link below:</p>
        <a href='{verification_link}' style="background:#6c63ff; color:white; padding:10px 20px;
           text-decoration:none; border-radius:6px; display:inline-block;">
           Verify Email Address
        </a>
        <p style="color:#888; margin-top:16px;">This link expires in 24 hours.</p>
    </div>
    """
    return _send_gmail(to_email, "Verify your email address - FinTrack", html)


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
            <td style="padding:8px 16px; border-bottom:1px solid #f0f0f0; text-align:right;
                color:#e74c3c;">₹{amount:,.2f}</td>
        </tr>'''

    savings_color = '#27ae60' if savings >= 0 else '#e74c3c'
    savings_label = 'Estimated Savings' if savings >= 0 else 'Estimated Deficit'

    html = f'''
    <div style="font-family:Arial,sans-serif; max-width:600px; margin:0 auto;
         background:#f8f9fa; padding:20px;">
        <div style="background:#4f46e5; padding:24px; border-radius:12px 12px 0 0;
             text-align:center;">
            <h2 style="color:white; margin:0;">FinTrack Expense Report</h2>
            <p style="color:#c7d2fe; margin:8px 0 0;">{next_month} Prediction</p>
        </div>
        <div style="background:white; padding:24px; border-radius:0 0 12px 12px;">
            <p style="color:#555;">Hi {user_name},</p>
            <p style="color:#555;">Based on your spending history, here is your predicted
               expense breakdown for <strong>{next_month}</strong>:</p>

            <div style="background:#fff3cd; border-radius:8px; padding:16px;
                 text-align:center; margin:16px 0;">
                <p style="margin:0; color:#856404; font-size:0.9rem;">Total Predicted Expenses</p>
                <h2 style="margin:8px 0 0; color:#e74c3c;">₹{total:,.2f}</h2>
            </div>

            <h4 style="color:#333; margin-top:24px;">Breakdown by Category</h4>
            <table style="width:100%; border-collapse:collapse; margin-top:8px;">
                <thead>
                    <tr style="background:#f8f9fa;">
                        <th style="padding:8px 16px; text-align:left; color:#888;
                            font-size:0.8rem;">CATEGORY</th>
                        <th style="padding:8px 16px; text-align:right; color:#888;
                            font-size:0.8rem;">PREDICTED AMOUNT</th>
                    </tr>
                </thead>
                <tbody>{category_rows}</tbody>
            </table>

            <div style="background:#f0fdf4; border-radius:8px; padding:16px;
                 text-align:center; margin:24px 0 8px;">
                <p style="margin:0; color:#555; font-size:0.9rem;">{savings_label}</p>
                <h2 style="margin:8px 0 0; color:{savings_color};">₹{abs(savings):,.2f}</h2>
            </div>

            <p style="color:#999; font-size:0.8rem; text-align:center; margin-top:24px;">
                This is an AI-based prediction using your past transactions.
                Actual amounts may vary.
            </p>
            <hr style="border:none; border-top:1px solid #eee;">
            <p style="color:#bbb; font-size:0.75rem; text-align:center;">
                FinTrack — Personal Finance Tracker
            </p>
        </div>
    </div>
    '''
    return _send_gmail(to_email, f'FinTrack — Your Expense Prediction for {next_month}', html)