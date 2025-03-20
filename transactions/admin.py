from django.contrib import admin

from transactions.models import Transaction, Withdrawal

admin.site.register(Transaction)
admin.site.register(Withdrawal)
