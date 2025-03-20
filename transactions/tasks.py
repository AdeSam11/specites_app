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
        address = profile.wallet_address
        balance = contract.functions.balanceOf(address) / 1_000_000

        # Check if balance > 0 and not already processed
        if balance >= 1:
            # Auto forward to owner wallet
            try:
                private_key = PrivateKey(bytes.fromhex(profile.private_key))
                txn = contract.functions.transfer(
                    settings.OWNER_TRON_WALLET,
                    int(balance * 1_000_000)
                ).with_owner(address).fee_limit(1_000_000).build().sign(private_key)

                txn.broadcast().wait()

                # Update user balance
                user_account = profile.user.account_profile
                user_account.balance += Decimal(balance)
                user_account.withdrawable_balance += Decimal(balance)
                user_account.save()

                # Log transaction
                Transaction.objects.create(
                    user=profile.user,
                    transaction_type='deposit',
                    amount=Decimal(balance),
                    status='completed'
                )

                # Send Email
                send_mail(
                    'Deposit Received',
                    f'Your deposit of ${balance} USDT has been received and credited to your balance. Start Investing Now!',
                    settings.EMAIL_HOST_USER,
                    [profile.user.email],
                    fail_silently=False
                )

            except Exception as e:
                print(f'Error forwarding for {address}: {e}')
