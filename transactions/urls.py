from django.urls import path

from transactions.views import deposit_money, nowpayments_webhook, deposit_success, deposit_failed, withdraw_money, deposit_history, create_withdrawal_password, withdrawal_history

app_name = 'transactions'


urlpatterns = [
    path("deposit/", deposit_money, name="deposit_money"),
    path("webhook/", nowpayments_webhook, name="nowpayments_webhook"),
    path("deposit-success/", deposit_success, name="deposit_success"),
    path("deposit-failed/", deposit_failed, name="deposit_failed"),
    path("deposit-history/", deposit_history, name="deposit_history"),
    path("withdraw/", withdraw_money, name="withdraw_money"),
    path("create-withdrawal-password/", create_withdrawal_password, name="create_withdrawal_password"),
    path("withdrawal-history/", withdrawal_history, name="withdrawal_history"),
]
