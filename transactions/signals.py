from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import UserProfile

User = get_user_model()

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Creates a profile for new users automatically."""
    if created:
        UserProfile.objects.create(user=instance)
    else:
        # Ensure profile exists for existing users
        UserProfile.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Saves the user profile whenever user instance is saved."""
    if hasattr(instance, "account_profile"):  # Prevents errors for users without profiles
        instance.account_profile.save()
