import requests
import json
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
from .models import CryptoDeposit, Withdrawal, UserProfile, Transaction

from django.contrib.auth import get_user_model

PLISIO_API_KEY = settings.PLISIO_API_KEY
PLISIO_API_URL = "https://api.plisio.net/api/v1/invoices/new"

@login_required
def deposit_money(request):
    if request.method == "POST":
        amount = request.POST.get("amount")

        if not amount or float(amount) < 10:
            messages.error(request, "Minimum deposit amount is $10.")
            return redirect("transactions:deposit_money")

        amount = float(amount)

        # Create a deposit record with "waiting" status
        deposit = CryptoDeposit.objects.create(
            user=request.user, 
            amount=amount, 
            payment_status="waiting"
        )

        # Prepare GET request parameters
        params = {
            "api_key": PLISIO_API_KEY,
            "order_number": str(deposit.id),
            "amount": amount,
            "order_name": f"Deposit for {request.user.first_name}",
            "success_callback_url": request.build_absolute_uri('/transactions/deposit-success/'),
            "fail_callback_url": request.build_absolute_uri('/transactions/deposit-failed/'),
            "callback_url": settings.PLISIO_CALLBACK_URL,
        }

        # Debugging print statement
        print("Sending GET request to Plisio:", PLISIO_API_URL, params)

        response = requests.get(PLISIO_API_URL, params=params)
        
        try:
            response_data = response.json()
        except requests.exceptions.JSONDecodeError:
            print("Plisio Response Error:", response.status_code, response.text)  # Debugging
            messages.error(request, "Invalid response from payment provider.")
            return redirect("transactions:deposit_money")

        print("Plisio Response:", response.status_code, response_data)  # Debugging

        if response.status_code == 200 and response_data.get("status") == "success":
            invoice_data = response_data.get("data", {})
            invoice_url = invoice_data.get("invoice_url")
            txn_id = invoice_data.get("txn_id")

            if invoice_url:
                # Update deposit record with invoice details
                deposit.transaction_id = txn_id
                deposit.save()

                # Redirect user to Plisio payment page
                return redirect(invoice_url)

        # If payment fails
        messages.error(request, response_data.get("message", "Payment failed."))
        return redirect("transactions:deposit_money")

    return render(request, "transactions/transaction_deposit.html")


@csrf_exempt
def plisio_webhook(request):
    """Handles Plisio payment updates."""
    if request.method in ["POST", "GET"]:
        try:
            data = {}

            if request.method == "POST":
                try:
                    # Attempt JSON body parsing
                    data = json.loads(request.body)
                    print("Parsed JSON from POST body.")
                except json.JSONDecodeError:
                    # Fallback to POST form-encoded data
                    data = request.POST.dict()
                    print("Parsed POST form data.")
            else:  # GET request
                data = request.GET.dict()
                print("Parsed data from GET request.")

            print("Webhook received:", json.dumps(data, indent=4))

            order_id = data.get("order_number")
            status = data.get("status")

            print(f"Order ID: {order_id}, Status: {status}")

            deposit = CryptoDeposit.objects.filter(id=order_id).first()
            if not deposit:
                print("Deposit not found.")
                return JsonResponse({"error": "Deposit not found"}, status=400)

            # Avoid processing the same deposit twice
            if deposit.payment_status.lower() in ["completed", "confirmed", "finished", "paid"]:
                print("Deposit already processed.")
                return JsonResponse({"status": "already_processed"}, status=200)

            deposit.payment_status = status
            deposit.save()

            if status in ["completed", "confirmed", "finished", "paid"]:
                amount_decimal = Decimal(deposit.amount)

                print(f"Updating balances for {deposit.user.username}, Amount: {amount_decimal}")

                deposit.user.account_profile.balance += amount_decimal
                deposit.user.account_profile.withdrawable_balance += amount_decimal
                deposit.user.account_profile.save()

                Transaction.objects.create(
                    user=deposit.user,
                    transaction_type="deposit",
                    amount=amount_decimal,
                    status=status
                )

                send_mail(
                    "Deposit Successful",
                    f"Your deposit of ${amount_decimal} USDT has been confirmed.",
                    settings.EMAIL_HOST_USER,
                    [deposit.user.email],
                    fail_silently=False,
                )

            else:
                print(f"Deposit not marked complete yet: {status}")

            return JsonResponse({"status": "success"}, status=200)

        except Exception as e:
            print("Webhook error:", str(e))
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request"}, status=400)

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

