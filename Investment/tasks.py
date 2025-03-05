from celery import shared_task
from django.utils.timezone import now
from .models import Investment

@shared_task
def update_daily_yield():
    """Automatically updates the user's total_yielded daily."""
    investments = Investment.objects.filter(matured_at__gt=now())  # Active investments
    for investment in investments:
        user_profile = investment.user.account_profile
        daily_yield = (investment.expected_return - investment.amount) / investment.plan_duration
        user_profile.total_yielded += daily_yield
        user_profile.balance += daily_yield
        user_profile.save()
