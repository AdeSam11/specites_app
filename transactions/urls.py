from django.urls import path

from transactions.views import deposit_money, deposit_invoice, verify_deposit, deposit_success, deposit_failed, withdraw_money, deposit_history, create_withdrawal_password, withdrawal_history, reset_withdrawal_password_request, reset_withdrawal_password

app_name = 'transactions'


urlpatterns = [
    path("deposit/", deposit_money, name="deposit_money"),
    path("invoice/", deposit_invoice, name="deposit_invoice"),
    path('verify-deposit/', verify_deposit, name='verify_deposit'),
    path("deposit-success/", deposit_success, name="deposit_success"),
    path("deposit-failed/", deposit_failed, name="deposit_failed"),
    path("deposit-history/", deposit_history, name="deposit_history"),
    path("withdraw/", withdraw_money, name="withdraw_money"),
    path("create-withdrawal-password/", create_withdrawal_password, name="create_withdrawal_password"),
    path("reset-withdrawal-password/", reset_withdrawal_password_request, name="reset_withdrawal_password_request"),
    path("reset-withdrawal-password/<int:user_id>/<str:token>/", reset_withdrawal_password, name="reset_withdrawal_password"),
    path("withdrawal-history/", withdrawal_history, name="withdrawal_history"),
]
