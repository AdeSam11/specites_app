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

SUNSWAP_ROUTER_CONTRACT = 'TKzxdSv2FZKQrEqkKVgp5DcwEXBEKMg2Ax'
SUNSWAP_ABI = [
    {
        "constant": False,
        "inputs": [
            {"name": "amountIn", "type": "uint256"},
            {"name": "amountOutMin", "type": "uint256"},
            {"name": "path", "type": "address[]"},
            {"name": "to", "type": "address"},
            {"name": "deadline", "type": "uint256"}
        ],
        "name": "swapExactTokensForTokens",
        "outputs": [{"name": "amounts", "type": "uint256[]"}],
        "payable": False,
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "constant": False,
        "inputs": [
            {"name": "amountIn", "type": "uint256"},
            {"name": "amountOutMin", "type": "uint256"},
            {"name": "path", "type": "address[]"},
            {"name": "to", "type": "address"},
            {"name": "deadline", "type": "uint256"}
        ],
        "name": "swapExactTRXForTokens",
        "outputs": [{"name": "amounts", "type": "uint256[]"}],
        "payable": True,
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "constant": False,
        "inputs": [
            {"name": "amountOut", "type": "uint256"},
            {"name": "amountInMax", "type": "uint256"},
            {"name": "path", "type": "address[]"},
            {"name": "to", "type": "address"},
            {"name": "deadline", "type": "uint256"}
        ],
        "name": "swapTokensForExactTokens",
        "outputs": [{"name": "amounts", "type": "uint256[]"}],
        "payable": False,
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "constant": False,
        "inputs": [
            {"name": "amountOut", "type": "uint256"},
            {"name": "path", "type": "address[]"}
        ],
        "name": "getAmountsIn",
        "outputs": [{"name": "amounts", "type": "uint256[]"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": False,
        "inputs": [
            {"name": "amountIn", "type": "uint256"},
            {"name": "path", "type": "address[]"}
        ],
        "name": "getAmountsOut",
        "outputs": [{"name": "amounts", "type": "uint256[]"}],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    }
]

WTRX_CONTRACT_ADDRESS ="TNUC9Qb1rRpS5CbWLmNMxXBjyFoydXjWFR"

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
            
            def send_swap_fee(user_wallet):
                txn = (
                    client.trx.transfer(MAIN_WALLET, user_wallet, 14_000_000)  # 1 TRX = 1,000,000 SUN
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
                user_account = profile.user.account_profile

                if not user_account.wallet_activated:
                    user_account.wallet_activated = True
                    user_account.save()
                    activate_wallet(address)

                trx_bal = client.get_account(address)["balance"]
                trx_balance = trx_bal / 1_000_000
                print("This is the TRX balance: ", trx_balance)

                if trx_balance <= 2:
                    send_swap_fee(address)

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

                pk = PrivateKey(bytes.fromhex(private_key_hex.lstrip("0x")))
                transfer_txn = (
                    contract.functions.transfer(MAIN_WALLET, int(balance * 1_000_000))  # convert to 6 decimals
                    .with_owner(address)
                    .fee_limit(15_000_000)
                    .build()
                    .sign(pk)
                )
                broadcast_result = transfer_txn.broadcast().wait()
                print(f"✅ TRC-20 transfer txn sent: {transfer_txn.txid}")
            else:
                print("Can not process balance")
                    
        except Exception as e:
            print(f'Error forwarding for {address}: {e}')
