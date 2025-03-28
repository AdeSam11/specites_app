from tronpy import Tron
from tronpy.contract import Contract
from tronpy.providers import HTTPProvider
from tronpy.keys import PrivateKey
from decimal import Decimal
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth.tokens import default_token_generator
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail
from .models import Withdrawal, Transaction, UserProfile

from django.contrib.auth import get_user_model

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

MAIN_WALLET = settings.OWNER_TRON_WALLET
MAIN_WALLET_PRIVATE_KEY = settings.OWNER_PRIV_KEY

@login_required
def deposit_money(request):
    if request.method == "POST":
        try:
            amount = Decimal(request.POST.get("amount", "0"))
        except:
            messages.error(request, "Invalid amount.")
            return redirect("transactions:deposit_money")
        if not amount or float(amount) < 10:
            messages.error(request, "Minimum deposit is $10.")
            return redirect("transactions:deposit_money")
        request.session['deposit_amount'] = amount
        return redirect("transactions:deposit_invoice")
    return render(request, "transactions/transaction_deposit.html")

@login_required
def deposit_invoice(request):
    amount = request.session.get('deposit_amount')
    profile = request.user.account_profile
    wallet_address = profile.wallet_address

    qr_code_url = f"https://quickchart.io/qr?text={wallet_address}&size=250"

    return render(request, "transactions/deposit_invoice.html", {
        "amount": amount,
        "wallet_address": wallet_address,
        "network": "TRC-20",
        "qr_code_url": qr_code_url
    })

@login_required
def verify_deposit(request):
    amount = Decimal(request.session.get('deposit_amount', 0))
    profile = request.user.account_profile
    user_address = profile.wallet_address

    def activate_wallet(user_wallet):
        txn = (
            client.trx.transfer(MAIN_WALLET, user_wallet, 1_000_000)  # 1 TRX = 1,000,000 SUN
            .build()
            .sign(PrivateKey(bytes.fromhex(MAIN_WALLET_PRIVATE_KEY)))
        )
        response = txn.broadcast().wait()
        return response
            
    activate_wallet(user_address)

    client = Tron(HTTPProvider(settings.TRON_RPC_URL))

    try:
        contract = client.get_contract(TRC20_USDT_CONTRACT)
        contract.abi = TRC20_ABI

        # Now safely call balanceOf
        balance_raw = contract.functions.balanceOf(user_address).call()
        balance = Decimal(balance_raw) / Decimal(1_000_000)

        if Decimal(balance) >= amount:
            return JsonResponse({"status": "success"})
        else:
            return JsonResponse({"status": "fail"})
        
    except Exception as e:
        print(f"[ERROR] Verifying deposit failed: {e}")
        return JsonResponse({"status": "error", "message": "Payment verification failed."})

@login_required
@csrf_exempt
def deposit_success(request):
    return render(request, "transactions/deposit_success.html")


@login_required
@csrf_exempt
def deposit_failed(request):
    return render(request, "transactions/deposit_failed.html")

@login_required
def deposit_history(request):
    deposits = Transaction.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "transactions/deposit_history.html", {"deposits": deposits})

@login_required
def withdraw_money(request):
    """Handles withdrawal requests."""

    # Ensures user has a profile
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        wallet_address = request.POST.get("wallet_address")
        amount = request.POST.get("amount")
        withdrawal_password = request.POST.get("withdrawal_password")

        # Validate amount
        if not amount or float(amount) < 10:
            messages.error(request, "Minimum withdrawal amount is $10.")
            return redirect("transactions:withdraw_money")

        amount = Decimal(amount)

        user_profile1 = request.user.account_profile

        # Ensure user has enough balance
        if amount > user_profile1.withdrawable_balance:
            messages.error(request, "Insufficient withdrawable balance.")
            return redirect("transactions:withdraw_money")

        # Check if the user has a withdrawal password
        if not user_profile.withdrawal_password:
            messages.error(request, "You must create a withdrawal password before proceeding.")
            return redirect("transactions:create_withdrawal_password")

        # Validate the entered withdrawal password
        if withdrawal_password != user_profile.withdrawal_password:
            messages.error(request, "Incorrect withdrawal password.")
            return redirect("transactions:withdraw_money")
        
        # Deduct from withdrawable balance
        user_profile1.balance -= amount
        user_profile1.withdrawable_balance -= amount
        
        user_profile.save()
        user_profile1.save()

        # Create a withdrawal request
        Withdrawal.objects.create(
            user=request.user,
            amount=amount,
            wallet_address=wallet_address,
            status="pending"
        )

        # Log transaction
        Transaction.objects.create(
            user=request.user,
            transaction_type="withdrawal",
            amount=amount,
            status="pending"
        )

        # Send email notification to specites
        send_mail(
            "New Withdrawal Request",
            f"User: {request.user.first_name} {request.user.last_name}\nEmail: {request.user.email}\nAmount: ${amount}\nWallet Address: {wallet_address} (TRC20)",
            settings.EMAIL_HOST_USER,
            [settings.EMAIL_HOST_USER],
            fail_silently=False,
        )

        messages.success(request, "Withdrawal request submitted. Pending approval.")
        return redirect("home")

    return render(request, "transactions/transaction_withdraw.html")


@login_required
def create_withdrawal_password(request):
    if request.user.transaction_profile.withdrawal_password:
        messages.warning(request, "You already have a withdrawal password.")
        return redirect("transactions:withdraw_money")
    
    if request.method == "POST":
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("transactions:create_withdrawal_password")

        request.user.transaction_profile.withdrawal_password = password
        request.user.transaction_profile.save()
        messages.success(request, "Withdrawal password set successfully.")
        return redirect("transactions:withdraw_money")

    return render(request, "transactions/create_withdrawal_password.html")

@login_required
def reset_withdrawal_password_request(request):
    """Handles sending an email with a reset link."""
    if request.method == "POST":
        user = request.user
        token = default_token_generator.make_token(user)
        reset_link = request.build_absolute_uri(reverse("transactions:reset_withdrawal_password", args=[user.pk, token]))

        # Send reset email
        send_mail(
            "Reset Your Withdrawal Password",
            f"Click the link to reset your withdrawal password: {reset_link}",
            settings.EMAIL_HOST_USER,
            [user.email],
            fail_silently=False,
        )

        messages.success(request, "A password reset link has been sent to your email.")
        return redirect("transactions:withdraw_money")

    return render(request, "transactions/reset_withdrawal_password_request.html")

@login_required
def reset_withdrawal_password(request, user_id, token):
    """Handles resetting the withdrawal password after clicking the reset link."""
    User = get_user_model()
    user = User.objects.filter(pk=user_id).first()

    if not user or not default_token_generator.check_token(user, token):
        messages.error(request, "Invalid or expired reset link.")
        return redirect("transactions:withdraw_money")

    if request.method == "POST":
        new_password = request.POST.get("new_password")
        confirm_password = request.POST.get("confirm_password")

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect(request.path)

        user.transaction_profile.withdrawal_password = new_password
        user.transaction_profile.save()

        messages.success(request, "Your withdrawal password has been reset successfully.")
        return redirect("transactions:withdraw_money")

    return render(request, "transactions/reset_withdrawal_password.html", {"user": user})

@login_required
def withdrawal_history(request):
    withdrawals = Withdrawal.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "transactions/withdrawal_history.html", {"withdrawals": withdrawals})

