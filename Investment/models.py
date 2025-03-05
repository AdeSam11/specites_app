from django.db import models
from django.conf import settings
from django.utils.timezone import now

class Investment(models.Model):
    PLAN_CHOICES = [
        (15, '10% for 15 days'),
        (30, '20% for 30 days'),
        (60, '45% for 60 days'),
        (90, '70% for 90 days'),
        (180, '150% for 180 days'),
        (365, '300% for 365 days'),
        (730, '600% for 730 days'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    plan_duration = models.IntegerField(choices=PLAN_CHOICES)
    expected_return = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    matured_at = models.DateTimeField()
    is_processed = models.BooleanField(default=False)  # Track if processed

    def progress_percentage(self):
        """Calculates how much progress the investment has made towards maturity."""
        total_duration = (self.matured_at - self.created_at).total_seconds()
        elapsed_time = (now() - self.created_at).total_seconds()
        return min(100, max(0, (elapsed_time / total_duration) * 100))
    
    def is_active(self):
        """Checks if the investment is still ongoing."""
        return now() < self.matured_at

    def __str__(self):
        return f"{self.user.username} - {self.get_plan_duration_display()} - ${self.amount}"
