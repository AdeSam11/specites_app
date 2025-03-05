from django.contrib import admin
from .models import Investment

@admin.register(Investment)
class InvestmentAdmin(admin.ModelAdmin):
    list_display = ("user", "amount", "plan_duration", "expected_return", "created_at", "matured_at")
