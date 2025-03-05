import os
from celery import Celery

# Set default Django settings module for Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'banking_system.settings')

# Create Celery application instance
app = Celery('banking_system')

# Load settings from Django settings.py
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed Django apps
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

from celery.schedules import crontab

app.conf.beat_schedule = {
    "update_daily_yield_every_day": {
        "task": "Investment.tasks.update_daily_yield",
        "schedule": crontab(hour=0, minute=0),  # Runs every midnight
    },
}
