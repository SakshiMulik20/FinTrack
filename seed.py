from app import create_app
from app.extensions import db
from app.models.category import Category

app = create_app()
with app.app_context():
    defaults = [
        ('Food & Dining', '🍔', '#f7931e'),
        ('Transport', '🚗', '#2196f3'),
        ('Shopping', '🛍️', '#9c27b0'),
        ('Entertainment', '🎬', '#e91e63'),
        ('Rent & Housing', '🏠', '#4caf50'),
        ('Health', '💊', '#00bcd4'),
        ('Travel', '✈️', '#ff5722'),
        ('Education', '📚', '#607d8b'),
        ('Salary', '💰', '#8bc34a'),
        ('Other', '📦', '#9e9e9e'),
    ]
    for name, icon, color in defaults:
        if not Category.query.filter_by(name=name, user_id=None).first():
            db.session.add(Category(name=name, icon=icon, color_hex=color))
    db.session.commit()
    print('Categories seeded successfully!')
    
    
    
