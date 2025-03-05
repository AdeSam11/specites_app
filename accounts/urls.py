from django.urls import path

from .views import UserRegistrationView, LogoutView, UserLoginView, VerifyEmailView, history_view


app_name = 'accounts'

urlpatterns = [
    path(
        "login/", UserLoginView.as_view(),
        name="user_login"
    ),
    path(
        "logout/", LogoutView.as_view(),
        name="user_logout"
    ),
    path(
        "register/", UserRegistrationView.as_view(),
        name="user_registration"
    ),
    path("verify-email/<int:user_id>/", VerifyEmailView.as_view(), name="verify_email"),
    path("history/", history_view, name="history"),
]
