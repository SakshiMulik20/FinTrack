from app import create_app
from extensions import celery

app = create_app()
app.app_context().push()