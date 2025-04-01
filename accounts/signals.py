from django.dispatch import receiver
from django.conf import settings
from django.db.models.signals import post_save
from django.contrib.auth import get_user_model
from tronpy import Tron
from tronpy.keys import PrivateKey
from tronpy.providers import HTTPProvider
from .models import Profile

from Crypto.Cipher import AES
import base64
import os

BLOCK_SIZE = 16  # AES block size

def pad(data):
    """Pad data to be a multiple of BLOCK_SIZE"""
    padding_length = BLOCK_SIZE - len(data) % BLOCK_SIZE
    return data + (chr(padding_length) * padding_length).encode()

def unpad(data):
    """Remove padding"""
    return data[:-ord(data[-1:])]

def encrypt_private_key(private_key: str) -> str:
    """Encrypt a private key using AES"""
    cipher = AES.new(settings.AES_SECRET_KEY1, AES.MODE_CBC, os.urandom(16))
    encrypted_data = cipher.encrypt(pad(private_key.encode()))
    return base64.b64encode(cipher.iv + encrypted_data).decode()

def decrypt_private_key(encrypted_private_key: str) -> str:
    """Decrypt a private key using AES"""
    raw_data = base64.b64decode(encrypted_private_key)
    iv = raw_data[:16]  # Extract IV
    encrypted_data = raw_data[16:]  # Extract encrypted part
    cipher = AES.new(settings.AES_SECRET_KEY1, AES.MODE_CBC, iv)
    return unpad(cipher.decrypt(encrypted_data)).decode()

User = get_user_model()

@receiver(post_save, sender=User)
def create_wallet_on_registration(sender, instance, created, **kwargs):
    if created:
        client = Tron(HTTPProvider(settings.TRON_RPC_URL))
        key = PrivateKey.random()
        address = key.public_key.to_base58check_address()

        # Encrypt the private key
        encrypted_private_key = encrypt_private_key(key.hex())

        Profile.objects.create(
            user=instance,
            wallet_address=address,
            private_key=encrypted_private_key
        )
