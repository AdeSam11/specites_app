from accounts.models import Profile
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import render, redirect
from django.core.mail import send_mail
from django.contrib import messages
from .forms import ContactForm
from Investment.models import Investment
from .models import Referral
from django.views.generic import TemplateView


def home(request):
    user_profile = None
    if not request.user.is_authenticated:
        investment_plans = [
            {"duration": f"{plan[0]} Days", "return": plan[1].split(" ")[0]} 
            for plan in Investment.PLAN_CHOICES
        ]

        top_investors = Profile.objects.select_related('user') \
            .order_by('-total_invested')[:10]

        return render(request, "core/index.html", {
            "investment_plans": investment_plans,
            "top_investors": top_investors
        })
    else:
        user_profile = getattr(request.user, 'account_profile', None)

        # Debugging: Create profile if missing
        if not user_profile:
            print(f"Profile missing for user: {request.user}. Creating one...")
            user_profile, created = Profile.objects.get_or_create(user=request.user)

    # Get top 10 investors ranked by total invested amount
    top_investors = Profile.objects.order_by('-total_invested')[:10]

    context = {
        'withdrawable_balance': getattr(user_profile, 'withdrawable_balance', 0.00),
        'ongoing_investment_balance': getattr(user_profile, 'ongoing_investment_balance', 0.00),
        'total_invested': getattr(user_profile, 'total_invested', 0.00),
        'total_yielded': getattr(user_profile, 'total_yielded', 0.00),
        'top_investors': top_investors
    }
    return render(request, 'core/home.html', context) 

class AboutView(TemplateView):
    template_name = 'core/about.html'

def about_view(request):
    form = ContactForm(request.POST)
    if form.is_valid():
        name = form.cleaned_data['name']
        email = form.cleaned_data['email']
        subject = form.cleaned_data['subject']
        message = form.cleaned_data['message']

        send_mail(
            f'Contact Form: {subject}',
            f'From: {name} <{email}>\n\n{message}',
            email,
            [settings.EMAIL_HOST_USER],  
            fail_silently=False,
        )

        messages.success(request, "Your message has been sent successfully!")
        return redirect('about')
    faqs = [
        {
            "question": "What is Specites, and how does it generate returns?",
            "answer": "Specites is an investment platform that leverages price discrepancies (through arbitrage trading) across different trading platforms to generate returns. We use automated software to buy assets (crypto and stocks) at lower prices on one platform and sell them at higher prices on another. We also capitalize on pre-listing opportunities, purchasing assets before they are publicly available and selling them at a profit after they are listed. You can read more about this at the “about” section"
        },
        {
            "question": "How is Specites able to offer high fixed interest rates?",
            "answer": "Our ability to offer high interest rates is based on high-frequency arbitrage trading due to market inefficiencies. Since our trading strategy involves multiple transactions per week with minimal exposure to market volatility, we consistently generate profits. These profits allow us to provide fixed returns to our investors."
        },
        {
            "question": "Is my investment at risk?",
            "answer": "Like any financial investment, there are inherent risks. However, our model significantly minimizes risk by focusing on arbitrage opportunities rather than speculative trading. Additionally, we use sophisticated software that has being tested for years before we launched Specites plus a well-structured strategy to manage risks effectively."
        },
        {
            "question": "How does the investment process work?",
            "answer": "1. You deposit funds into your Specites account \n 2. Choose any product or investment plan of your choice \n 3. Wait till the maturity date and both your money (the principal) and your interest will be paid into your withdrawable balance automatically"
        },
        {
            "question": "Can I withdraw my investment at any time?",
            "answer": "When you deposit money, it goes into your withdrawable balance and can be withdrawn at any time whether or not you invest it. However, once you invest the money you can’t withdraw it until the maturity date is reached and after which, both the money and the interest earned on it will be moved to your withdrawable balance which you can withdraw."
        },
        {
            "question": "Can I cancel my investment at any time?",
            "answer": "You can only cancel an investment plan of 30 days and above. In which case, before you can cancel it the investment would have lasted for at least 2 weeks (14 days), after which you can write us a mail or chat with our live customer support team and it’ll be cancelled for you. You should however be reminded that if you cancel your investment, you won’t be paid any interest - just your money (the principal)."
        },
        {
            "question": "What are the minimum and maximum investment amounts?",
            "answer": "The minimum investment amounts is 10 USDT and there is no maximum investment amount."
        },
        {
            "question": "What is the minimum and maximum amount I can deposit and withdraw?",
            "answer": "The minimum amount you can deposit is 10 USDT \n The maximum amount you can deposit per transaction is 1,000,000 USDT \n The minimum amount you can withdraw is 10 USDT \n The Maximum amount you can withdraw per day is unlimited, however the maximum amount you can withdraw per transaction is 1,000,000 USDT \n There are no withdrawal or deposit fees"
        },
        {
            "question": "How long does it take for my withdrawals and deposits to reflect in my accounts?",
            "answer": "A maximum of 1 hour, be it withdrawal or deposit."
        },
        {
            "question": "Do you process fiat currency?",
            "answer": "N0. All our transactions are done using USDT"
        },
        {
            "question": "How secure is my investment with Specites?",
            "answer": "Security is a top priority at Specites. We use advanced encryption, multi-factor authentication, and secure wallets to protect investor funds. Additionally, our trading model minimizes exposure to market risks, ensuring a more stable investment experience."
        },
        {
            "question": "Are there any hidden fees or charges?",
            "answer": "No hidden fees. No hidden charges. What you see is what you get."
        },
        {
            "question": "How does Specites identify profitable opportunities?",
            "answer": "We use software that we developed and have tested for years. The software scans hundreds of trading platforms daily to detect price discrepancies. It identifies where an asset is being sold at a lower price and where it can be sold at a higher price, allowing us to execute trades for profit."
        },
        {
            "question": "Does Specites trade only in crypto, or are other assets included?",
            "answer": "For now, our primary focus is majorly crypto and a little of stocks. Also, our strategies and an AI-powered software is currently being worked on to enable us branch into other financial assets in the future."
        },
        {
            "question": "How can I monitor my investment?",
            "answer": "Click on the “Portfolio” icon at the bottom, when logged In, and you’ll be able to track your investment, interest earnings, and transaction history in real-time."
        },
        {
            "question": "What happens if there are market fluctuations?",
            "answer": "Since our trading strategy is based on arbitrage, we are largely unaffected by market fluctuations. Unlike traditional trading, where profits depend on market direction, our strategy profits from price differences across platforms, making it more stable."
        },
        {
            "question": "How can I contact Specites for further inquiries?",
            "answer": "You can reach us via email and live chat. We also encourage investors to check our FAQs and help center for quick answers to common questions."
        },
    ]

    return render(request, "core/about.html", {"faqs": faqs, "form": form})

@login_required
def referral_view(request):
    return render(request, "core/refer.html")


@login_required
def referral_history(request):
    """Displays the list of users referred by the logged-in user and their investment status."""
    referrals = Referral.objects.filter(referrer=request.user).select_related("referred_user")

    context = {
        "referrals": referrals,
    }
    return render(request, "core/referral_history.html", context)

@login_required
def profile_view(request):
    user = request.user
    password_form = PasswordChangeForm(user=request.user)

    if request.method == "POST":
        password_form = PasswordChangeForm(user=request.user, data=request.POST)
        if password_form.is_valid():
            password_form.save()
            update_session_auth_hash(request, password_form.user)
            messages.success(request, "Your password has been updated successfully!")

    return render(request, "core/profile.html", {"user": user, "password_form": password_form})

@login_required
def help_support_view(request):
    return render(request, "core/help_support.html")