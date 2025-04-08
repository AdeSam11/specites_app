from django.core.mail import send_mail
from django.utils.crypto import get_random_string
from django.contrib import messages
from django.contrib.auth import get_user_model, logout
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import RedirectView, View
from core.models import Referral
from accounts.models import User
from .forms import UserRegistrationForm, EmailAuthenticationForm
from .models import EmailVerificationOTP



User = get_user_model()


class UserRegistrationView(View):
    template_name = "accounts/user_registration.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("home")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        # Pre-fill referral code from URL if available
        referral_code = request.GET.get("ref", "")
        form = UserRegistrationForm(initial={"referral_code": referral_code})
        return render(request, self.template_name, {"form": form})

    def post(self, request, *args, **kwargs):
        form = UserRegistrationForm(request.POST)

        if form.is_valid():
            # Handle referral
            referral_code = form.cleaned_data.get("referral_code")
            if referral_code:
                try:
                    referrer_profile = User.objects.get(referral_code=referral_code)
                    user = form.save()
                    Referral.objects.create(referrer=referrer_profile, referred_user=user)
                except User.DoesNotExist:
                    messages.error(request, "Invalid referral code, try again")
                    return render(request, self.template_name, {"form": form})
        
            user = form.save(commit=False)
            user.country_code = form.cleaned_data['country_code']
            user = form.save()
            
            # Generate OTP and send email
            otp_code = get_random_string(length=6, allowed_chars='1234567890')  # 6-digit OTP
            EmailVerificationOTP.objects.create(user=user, otp=otp_code)

            send_mail(
                "Verify Your Email",
                f"Your OTP for email verification is: {otp_code}",
                "support@specites.com",
                [user.email],
                fail_silently=False,
            )

            messages.info(request, "An OTP has been sent to your email. Please verify to continue.")
            return redirect("accounts:verify_email", user_id=user.id)  # Redirect to OTP page

        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.capitalize()}: {error}")
        return render(request, self.template_name, {"form": form})


class UserLoginView(LoginView):
    template_name = 'accounts/user_login.html'
    authentication_form = EmailAuthenticationForm 
    redirect_authenticated_user = True

    def form_invalid(self, form):
        print("Form errors:", form.errors)
        messages.error(self.request, "Invalid email or password. Please try again.")
        return self.render_to_response(self.get_context_data(form=form))


class LogoutView(RedirectView):
    pattern_name = 'home'

    def get_redirect_url(self, *args, **kwargs):
        if self.request.user.is_authenticated:
            logout(self.request)
        return super().get_redirect_url(*args, **kwargs)

@login_required
def history_view(request):
    return render(request, "accounts/user_history.html")

class VerifyEmailView(View):
    template_name = "accounts/verify_email.html"

    def get(self, request, user_id):
        return render(request, self.template_name, {"user_id": user_id})

    def post(self, request, user_id):
        otp_entered = request.POST.get("otp")
        try:
            user = User.objects.get(id=user_id)
            otp_record = EmailVerificationOTP.objects.get(user=user)

            if otp_record.is_expired():
                messages.error(request, "OTP has expired. Please register again.")
                user.delete()  # Remove unverified user
                return redirect("accounts:user_registration")

            if otp_record.otp == otp_entered:
                user.is_active = True
                user.save()
                otp_record.delete()  # Remove OTP after verification
                messages.success(request, "Email verified successfully! You can now log in.")
                return redirect(reverse_lazy("accounts:user_login"))
            else:
                messages.error(request, "Invalid OTP. Try again.")

        except (User.DoesNotExist, EmailVerificationOTP.DoesNotExist):
            messages.error(request, "Invalid request. Please register again.")
            return redirect("accounts:user_registration")

        return render(request, self.template_name, {"user_id": user_id})