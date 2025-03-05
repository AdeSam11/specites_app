from django.contrib.auth.views import PasswordResetView
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.urls import reverse_lazy
from django.shortcuts import redirect

User = get_user_model()

class CustomPasswordResetView(PasswordResetView):
    template_name = "core/password_reset.html"
    email_template_name = "core/password_reset_email.txt"
    subject_template_name = "core/password_reset_subject.txt"
    success_url = reverse_lazy("password_reset_done")

    def form_valid(self, form):
        email = form.cleaned_data.get("email")
        if not User.objects.filter(email=email).exists():
            messages.error(self.request, "This email is not registered in our system.")
            return redirect("password_reset")  # Redirect back to the reset form
        return super().form_valid(form)
