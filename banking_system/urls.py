"""banking_system URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from django.contrib.auth import views as auth_views

from .views import CustomPasswordResetView
from core.views import home, about_view, profile_view, help_support_view


urlpatterns = [
    path('', home, name='home'),
    path('about/', about_view, name='about'),
    path('profile/', profile_view, name='profile'),
    path('help/', help_support_view, name='help'),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('trade/', include('trade.urls', namespace='trade')),
    path('core/', include('core.urls', namespace='core')),
    path('invest/', include('Investment.urls', namespace='Investment')),
    path('admin/', admin.site.urls),
    path(
        'transactions/',
        include('transactions.urls', namespace='transactions')
    ),
    path("password_reset/", CustomPasswordResetView.as_view(), name="password_reset"),
    path("password_reset_done/", auth_views.PasswordResetDoneView.as_view(template_name="core/password_reset_done.html"), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(template_name="core/password_reset_confirm.html"), name="password_reset_confirm"),
    path("reset/done/", auth_views.PasswordResetCompleteView.as_view(template_name="core/password_reset_complete.html"), name="password_reset_complete"),
]
