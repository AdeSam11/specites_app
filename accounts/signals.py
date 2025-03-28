from django.dispatch import receiver
from django.conf import settings
from django.db.models.signals import post_save
from django.contrib.auth import get_user_model
from tronpy import Tron
from tronpy.keys import PrivateKey
from tronpy.providers import HTTPProvider
from .models import Profile
from cryptography.fernet import Fernet

User = get_user_model()

@receiver(post_save, sender=User)
def create_wallet_on_registration(sender, instance, created, **kwargs):
    if created:
        client = Tron(HTTPProvider(settings.TRON_RPC_URL))
        key = PrivateKey.random()
        address = key.public_key.to_base58check_address()

        # Encrypt the private key
        fernet = Fernet(settings.FERNET_SECRET_KEY.encode())
        encrypted_private_key = fernet.encrypt(key.hex().encode()).decode()

        Profile.objects.create(
            user=instance,
            wallet_address=address,
            private_key=encrypted_private_key
        )
