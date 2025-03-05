from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.contrib.auth import get_user_model

User = get_user_model()

class CryptoDeposit(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("failed", "Failed"),
    ]

    user = models.ForeignKey(User, related_name='deposit', on_delete=models.CASCADE)
    amount = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(10)]
    )
    payment_id = models.CharField(max_length=255, unique=False)
    payment_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    transaction_id = models.CharField(max_length=100, unique=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.amount} USDT - {self.payment_status}"


class Withdrawal(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    wallet_address = models.CharField(max_length=255)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    withdrawal_password = models.CharField(max_length=128)  # Store securely, hash it

    def __str__(self):
        return f"Withdrawal {self.id} - {self.user.username}"
    
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="transaction_profile")
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)  
    withdrawable_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    withdrawal_password = models.CharField(max_length=100, blank=True, null=True)  # Can be encrypted later

    def __str__(self):
        return f"{self.user.username}'s Profile"
    
