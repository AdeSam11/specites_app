import requests
import json
from decimal import Decimal, ROUND_DOWN
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.utils.crypto import get_random_string
from django.urls import reverse
from django.contrib.auth.tokens import default_token_generator
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail
from .models import CryptoDeposit, Withdrawal, UserProfile

from django.contrib.auth import get_user_model

# NOWPayments API credentials
NOWPAYMENTS_API_KEY = settings.NOWPAYMENTS_API_KEY
NOWPAYMENTS_API_URL = "https://api.nowpayments.io/v1/invoice"
NOWPAYMENTS_RATE_API = "https://api.nowpayments.io/v1/rate"

@login_required
def deposit_money(request):
    if request.method == "POST":
        amount = request.POST.get("amount")

        if not amount or float(amount) < 10:
            messages.error(request, "Minimum deposit amount is $10.")
            return redirect("transactions:deposit_money")

        amount = float(amount)

        # Prepare API request
        headers = {
            "x-api-key": NOWPAYMENTS_API_KEY,
            "Content-Type": "application/json"
        }
        
        # Create a deposit record with "waiting" status
        deposit = CryptoDeposit.objects.create(
            user=request.user, amount=amount, payment_status="waiting"
        )

        payload = {
            "price_amount": float(amount),
            "price_currency": "usdttrc20",
            "pay_currency": "usdttrc20",  
            "ipn_callback_url": settings.NOWPAYMENTS_CALLBACK_URL,
            "order_id": str(deposit.id),
            "order_description": f"Deposit for {request.user.username}",
            "success_url": request.build_absolute_uri('/transactions/deposit-success/'),
            "cancel_url": request.build_absolute_uri('/transactions/deposit-failed/'),
        }

        # Debugging print statements
        print("Sending payload to NOWPayments:", json.dumps(payload, indent=4))

        response = requests.post(NOWPAYMENTS_API_URL, headers=headers, json=payload)
        
        try:
            response_data = response.json()
        except json.JSONDecodeError:
            messages.error(request, "Invalid response from payment provider.")
            return redirect("transactions:deposit_money")

        print("NOWPayments Response:", response.status_code, response_data)  # Debugging

        if response.status_code == 200 and "invoice_url" in response_data:
            return redirect(response_data["invoice_url"])
        else:
            messages.error(request, response_data.get("message", "Payment failed."))
            return redirect("transactions:deposit_money")

    return render(request, "transactions/transaction_deposit.html")


@csrf_exempt
def nowpayments_webhook(request):
    """Handles NOWPayments payment updates."""
    if request.method == "POST":
        try:
            data = json.loads(request.body)  # Load JSON data

            print("Webhook received:", json.dumps(data, indent=4))  # Debugging

            payment_id = data.get("payment_id")
            status = data.get("payment_status")
            order_id = data.get("order_id")

            deposit = CryptoDeposit.objects.filter(id=order_id).first()
            if not deposit:
                return JsonResponse({"error": "Deposit not found"}, status=400)

            deposit.payment_status = status
            deposit.save()

            if status in ["confirmed", "finished"]:
                deposit.amount = Decimal(deposit.amount)

                # Update user balances
                deposit.user.account_profile.balance += deposit.amount
                deposit.user.account_profile.withdrawable_balance += deposit.amount
                deposit.user.account_profile.save()

                # Send Email Notification
                send_mail(
                    "Deposit Successful",
                    f"Your deposit of ${deposit.amount} USDT has been confirmed.",
                    settings.EMAIL_HOST_USER,
                    [deposit.user.email],
                    fail_silently=False,
                )

            return JsonResponse({"status": "success"}, status=200)

        except Exception as e:
            print("Webhook error:", str(e))  # Debugging
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request"}, status=400)

@login_required
def deposit_success(request):
    return render(request, "transactions/deposit_success.html")


@login_required
def deposit_failed(request):
    return render(request, "transactions/deposit_failed.html")

@login_required
def deposit_history(request):
    deposits = CryptoDeposit.objects.filter(user=request.user).order_by("-created_at")
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

        # Send email notification to specites
        send_mail(
            "New Withdrawal Request",
            f"User: {request.user.first_name} {request.user.last_name}\nEmail: {request.user.email}\nAmount: ${amount}\nWallet Address: {wallet_address} (TRC20)",
            settings.EMAIL_HOST_USER,
            [settings.EMAIL_HOST_USER],
            fail_silently=False,
        )

        messages.success(request, "Withdrawal request submitted. Pending approval.")
        return redirect("core:home")

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

