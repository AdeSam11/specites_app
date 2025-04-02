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
                    client.trx.transfer(MAIN_WALLET, user_wallet, 2_000_000)  # 1 TRX = 1,000,000 SUN
                    .build()
                    .sign(PrivateKey(bytes.fromhex(MAIN_WALLET_PRIVATE_KEY.lstrip("0x"))))
                )
                response = txn.broadcast().wait()
                print("Transaction response:", response)
                return response
            
            def send_swap_fee(user_wallet):
                txn = (
                    client.trx.transfer(MAIN_WALLET, user_wallet, 3_000_000)  # 1 TRX = 1,000,000 SUN
                    .build()
                    .sign(PrivateKey(bytes.fromhex(MAIN_WALLET_PRIVATE_KEY.lstrip("0x"))))
                )
                response = txn.broadcast().wait()
                print("Transaction response:", response)
                return response
                
            if not profile.wallet_activated:
                activate_wallet(address)

                profile.wallet_activated = True
                profile.save()
            
            private_key_hex = decrypt_private_key(profile.private_key)
            
            # Fetch balance
            balance_raw = contract.functions.balanceOf(address)
            balance = Decimal(balance_raw) / Decimal(1_000_000)
            print("This is the USDT balance:", balance)

            if balance >= Decimal('9'):
                    trx_bal = client.get_account(address)["balance"]
                    trx_balance = trx_bal / 1_000_000
                    print("This is the TRX balance: ", trx_balance)

                    if trx_balance <= 2:
                        send_swap_fee(address)

                    # Update user balances
                    user_account = profile.user.account_profile
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

                    # Swap USDT to TRX using SunSwap API
                    PATH = [TRC20_USDT_CONTRACT, WTRX_CONTRACT_ADDRESS]
                    pk = PrivateKey(bytes.fromhex(private_key_hex.lstrip("0x")))
                    approve_txn = (
                        contract.functions.approve(SUNSWAP_ROUTER_CONTRACT, balance_raw)
                        .with_owner(address)
                        .fee_limit(5_000_000)
                        .build()
                        .sign(pk)
                    )
                    approve_txn.broadcast().wait()
                    print("✅ Approval transaction sent:", approve_txn.txid)

                    balance_raw2 = contract.functions.balanceOf(address)
                    balance2 = Decimal(balance_raw2) / Decimal(1_000_000)
                    print("New balance to be swapped:", balance2)

                    sun_swap_contract = client.get_contract(SUNSWAP_ROUTER_CONTRACT)

                    amount_in = balance_raw2
                    expected_out = sun_swap_contract.functions.getAmountsOut(amount_in, PATH)
                    amount_out_min = expected_out[-1] * Decimal('0.98')

                    swap_txn = (
                        sun_swap_contract.functions.swapExactTokensForTokens(
                            amount_in,
                            amount_out_min,
                            PATH,
                            address,
                            client.get_latest_block_number() + 500  # Expiry block
                        )
                        .with_owner(address)
                        .fee_limit(10_000_000)
                        .build()
                        .sign(pk)
                    )
                    swap_txn.broadcast().wait()
                    print("✅ Swap transaction sent:", swap_txn.txid)

                    trx_balance = client.get_account(address)["balance"]
                    print(f"🎉 New TRX Balance: {trx_balance / 1_000_000} TRX")

                    # Transfer TRX from user to owner wallet
                    reserved_trx = Decimal('3')
                    trx_to_transfer = int((trx_balance - reserved_trx) * Decimal(1_000_000))
                    transfer_txn = (
                        client.trx.transfer(address, MAIN_WALLET, trx_to_transfer)
                        .build()
                        .sign(pk)
                    )
                    transfer_txn.broadcast().wait()
                    txn_hash = transfer_txn.txid

                    # Log transaction
                    Transaction.objects.create(
                        user=profile.user,
                        transaction_type='deposit',
                        amount=balance,
                        status='completed',
                        reference=txn_hash  # Store txn hash
                    )
        except Exception as e:
            print(f'Error forwarding for {address}: {e}')
