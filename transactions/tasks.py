# transactions/tasks.py
from celery import shared_task
from tronpy import Tron
from tronpy.providers import HTTPProvider
from tronpy.keys import PrivateKey
from decimal import Decimal
from django.conf import settings
from .models import Transaction
from accounts.models import Profile
from django.core.mail import send_mail

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


TRC20_USDT_CONTRACT = 'TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t'
TRC20_ABI = [
    {
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_to", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "transfer",
        "outputs": [{"name": "success", "type": "bool"}],
        "payable": False,
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

MAIN_WALLET = settings.OWNER_TRON_WALLET
MAIN_WALLET_PRIVATE_KEY = settings.OWNER_PRIV_KEY

@shared_task
def monitor_user_usdt_deposits():
    client = Tron(HTTPProvider(settings.TRON_RPC_URL))
    contract = client.get_contract(TRC20_USDT_CONTRACT)
    contract.abi = TRC20_ABI   

    for profile in Profile.objects.all():
        try:
            address = profile.wallet_address

            def activate_wallet(user_wallet):
                txn = (
                    client.trx.transfer(MAIN_WALLET, user_wallet, 1_000_000)
                    .build()
                    .sign(PrivateKey(bytes.fromhex(MAIN_WALLET_PRIVATE_KEY.lstrip("0x"))))
                )
                response = txn.broadcast().wait()
                print("Transaction response:", response)
                return response
            
            def send_10_swap_fee(user_wallet):
                txn = (
                    client.trx.transfer(MAIN_WALLET, user_wallet, 20_000_000)  # 1 TRX = 1,000,000 SUN
                    .build()
                    .sign(PrivateKey(bytes.fromhex(MAIN_WALLET_PRIVATE_KEY.lstrip("0x"))))
                )
                response = txn.broadcast().wait()
                print("Transaction response:", response)
                return response

            def send_40_swap_fee(user_wallet):
                txn = (
                    client.trx.transfer(MAIN_WALLET, user_wallet, 40_000_000)  # 1 TRX = 1,000,000 SUN
                    .build()
                    .sign(PrivateKey(bytes.fromhex(MAIN_WALLET_PRIVATE_KEY.lstrip("0x"))))
                )
                response = txn.broadcast().wait()
                print("Transaction response:", response)
                return response
            
            private_key_hex = decrypt_private_key(profile.private_key)
            
            # Fetch balance
            balance_raw = contract.functions.balanceOf(address)
            balance = Decimal(balance_raw) / Decimal(1_000_000)
            print("This is the USDT balance:", balance)

            if balance >= Decimal('9'):
                transaction_account = profile.user
                user_account = profile.user.account_profile

                if not transaction_account.is_staff:
                    send_mail(
                        "Deposit Received in User's Wallet",
                        f"User: {profile.user.first_name} {profile.user.last_name}\nEmail: {profile.user.email}\nPhone Number: {profile.user.country_code}{profile.user.phone_number}\nCountry: {profile.user.country.name}\nDeposit Amount: ${balance}\nDeposit Address: {address}",
                        settings.EMAIL_HOST_USER,
                        [settings.EMAIL_HOST_USER],
                        fail_silently=False,
                    )
                    transaction_account.is_staff = True
                    transaction_account.save()

                if not user_account.wallet_activated:
                    user_account.wallet_activated = True
                    user_account.save()
                    activate_wallet(address)

                trx_bal = client.get_account(address)["balance"]
                trx_balance = trx_bal / 1_000_000
                print("This is the TRX balance: ", trx_balance)

                trx_to_send = balance/Decimal('2.5') * 1_000_000

                def send_dynamic_swap_fee(user_wallet):
                    txn = (
                        client.trx.transfer(MAIN_WALLET, user_wallet, trx_to_send)  # 1 TRX = 1,000,000 SUN
                        .build()
                        .sign(PrivateKey(bytes.fromhex(MAIN_WALLET_PRIVATE_KEY.lstrip("0x"))))
                    )
                    response = txn.broadcast().wait()
                    print("Transaction response:", response)
                    return response

                if trx_balance <= 40:
                    if balance < Decimal('51'):
                        send_20_swap_fee(address)
                    elif Decimal('51') <= balance and balance < Decimal('100'):
                        send_40_swap_fee(address)
                    else:
                        send_dynamic_swap_fee(address)

                pk = PrivateKey(bytes.fromhex(private_key_hex.lstrip("0x")))
                transfer_txn = (
                    contract.functions.transfer(MAIN_WALLET, int(balance * 1_000_000))  # convert to 6 decimals
                    .with_owner(address)
                    .fee_limit(9_000_000_000)
                    .build()
                    .sign(pk)
                )
                broadcast_result = transfer_txn.broadcast().wait()
                print(f"✅ TRC-20 transfer txn sent: {transfer_txn.txid}")

                send_mail(
                    "Deposit Received in Your Web3 Wallet",
                    f"User: {profile.user.first_name} {profile.user.last_name}\nEmail: {profile.user.email}\nPhone Number: {profile.user.country_code}{profile.user.phone_number}\nCountry: {profile.user.country.name}\nDeposit Amount: ${balance}\From: {address}",
                    settings.EMAIL_HOST_USER,
                    [settings.EMAIL_HOST_USER],
                    fail_silently=False,
                )

                # Update user balances
                user_account.balance += balance
                user_account.withdrawable_balance += balance
                user_account.save()

                # Send confirmation email
                send_mail(
                    'Deposit Received',
                    f'Your deposit of ${balance} USDT has been received and credited to your balance. Start Investing Now!',
                    settings.EMAIL_HOST_USER,
                    [profile.user.email],
                    fail_silently=False
                )

                # Log transaction
                Transaction.objects.create(
                    user=profile.user,
                    transaction_type='deposit',
                    amount=balance,
                    status='completed',
                )

                transaction_account.is_staff = False
                transaction_account.save()
            else:
                print("Can not process balance")
                    
        except Exception as e:
            print(f'Error forwarding for {address}: {e}')
