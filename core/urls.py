from django.urls import path

from .views import referral_view, referral_history

app_name = 'core'


urlpatterns = [
    path('refer/', referral_view, name="refer_earn"),
    path('referral_history/', referral_history, name="referral_history"),
]
