import random
import string
from django_countries.fields import CountryField
from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import UserManager


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True, null=False, blank=False)
    phone_number = models.CharField(max_length=15, unique=True, blank=False, null=False)
    country_code = models.CharField(max_length=6, blank=False, null=True)  # Store country code separately
    country = CountryField(blank_label="(Select country)")

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['phone_number']

    city = models.CharField(max_length=256)
    referral_code = models.CharField(max_length=10, unique=True)
    referral_bonus = models.DecimalField(default=0.00, max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        if not self.referral_code:  
            self.referral_code = self.generate_referral_code()
        super().save(*args, **kwargs)

    def generate_referral_code(self):
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        while User.objects.filter(referral_code=code).exists():
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        return code


class Profile(models.Model):
    user = models.OneToOneField(
        User,
        related_name='account_profile',
        on_delete=models.CASCADE
    )
    date_of_birth = models.DateField(null=True, blank=True)
    national_id_number = models.CharField(max_length=50, null=True, blank=True)
    
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    withdrawable_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    ongoing_investment_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_invested = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_yielded = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.user.username} - ${self.withdrawable_balance}"
    
class EmailVerificationOTP(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        from django.utils import timezone
        from datetime import timedelta
        return self.created_at + timedelta(minutes=10) < timezone.now()  # OTP expires in 10 mins
