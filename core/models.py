from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Referral(models.Model):
    referrer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="referrals")
    referred_user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="referred_by", null=True, blank=True)
    bonus_received = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.referrer} referred {self.referred_user}"

