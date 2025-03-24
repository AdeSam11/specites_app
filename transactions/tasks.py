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

TRC20_USDT_CONTRACT = 'TXLAQ63Xg1NAzckPwKHvzw7CSEmLMEqcdj'
TRC20_ABI = [
    {
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

@shared_task
def monitor_user_usdt_deposits():
    client = Tron(HTTPProvider(settings.TRON_RPC_URL))
    contract = client.get_contract(TRC20_USDT_CONTRACT)
    contract.abi = TRC20_ABI

    for profile in Profile.objects.all():
        try:
            address = profile.wallet_address
            private_key_hex = profile.private_key
            owner_wallet = settings.OWNER_TRON_WALLET
            
            # Fetch balance
            balance_raw = contract.functions.balanceOf(address).call()
            balance = Decimal(balance_raw) / Decimal(1_000_000)

            if balance >= Decimal('1'):
                    # Prepare transfer
                    private_key = PrivateKey(bytes.fromhex(private_key_hex))
                    amount_to_transfer = int((balance * Decimal(1_000_000)).to_integral_value())

                    txn = contract.functions.transfer(
                        owner_wallet,
                        amount_to_transfer
                    ).with_owner(address).fee_limit(1_000_000).build().sign(private_key)

                    txn_hash = txn.txid
                    txn.broadcast().wait()

                    # Update user balances
                    user_account = profile.user.account_profile
                    user_account.balance += balance
                    user_account.withdrawable_balance += balance
                    user_account.save()

                    # Log transaction
                    Transaction.objects.create(
                        user=profile.user,
                        transaction_type='deposit',
                        amount=balance,
                        status='completed',
                        reference=txn_hash  # Store txn hash
                    )

                    # Send confirmation email
                    send_mail(
                        'Deposit Received',
                        f'Your deposit of ${balance} USDT has been received and credited to your balance. Start Investing Now!',
                        settings.EMAIL_HOST_USER,
                        [profile.user.email],
                        fail_silently=False
                    )
        except Exception as e:
            print(f'Error forwarding for {address}: {e}')
