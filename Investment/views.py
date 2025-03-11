from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.timezone import now, timedelta
from .models import Investment
from core.models import Referral
from .forms import InvestmentForm

@login_required
def invest_view(request):
    if request.method == "POST":
        form = InvestmentForm(request.POST)
        if form.is_valid():
            investment = form.save(commit=False)
            investment.user = request.user

            # Investment rates based on duration
            investment_rate = {
                15: 1.1, 30: 1.2, 60: 1.45, 
                90: 1.7, 180: 2.5, 365: 4.0, 730: 7.0
            }

            # Calculate expected return
            if investment.plan_duration not in investment_rate:
                messages.error(request, "Invalid investment plan duration.")
                return redirect("investment:invest")

            expected_return = float(investment.amount) * investment_rate[investment.plan_duration]
            investment.expected_return = expected_return
            investment.matured_at = now() + timedelta(days=investment.plan_duration)

            # Get user's transaction profile
            user_profile = request.user.account_profile  

            # Check if user has enough balance
            if investment.amount > user_profile.balance:
                messages.error(request, "Insufficient balance. Please deposit more funds.")
                return redirect("investment:invest")

            # Deduct balance and save changes
            user_profile.withdrawable_balance -= investment.amount  # Ensure withdrawable balance is updated
            user_profile.total_invested += investment.amount
            user_profile.ongoing_investment_balance = investment.amount
            
            user_profile.save()
            investment.save()

            # Check if user was referred and bonus is not yet given
            referral = Referral.objects.filter(referred_user=request.user, bonus_received=False).first()
            if referral:
                referrer_profile = referral.referrer
                referrer_profile.referral_bonus += 2  # Give the $2 bonus
                referrer_profile.account_profile.balance += 2
                referrer_profile.account_profile.withdrawable_balance += 2
                referrer_profile.save()
                referral.bonus_received = True  # Mark bonus as given
                referral.save()

            messages.success(request, "Investment successful!")
            return redirect("Investment:portfolio")

    else:
        form = InvestmentForm()

    return render(request, "Investment/invest_index.html", {"form": form})

@login_required
def investment_history(request):
    investments = Investment.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "Investment/investment_history.html", {"investments": investments})


@login_required
def portfolio_view(request):
    # Fetch ongoing investments
    ongoing_investments = Investment.objects.filter(user=request.user, matured_at__gt=now())

    # Calculate total ongoing investment and expected return
    total_invested = sum(inv.amount for inv in ongoing_investments)
    expected_total = sum(inv.expected_return for inv in ongoing_investments)

    context = {
        "ongoing_investments": ongoing_investments,
        "total_invested": total_invested,
        "expected_total": expected_total,
    }
    return render(request, "Investment/portfolio.html", context)