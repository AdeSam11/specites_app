from django.urls import path
from .views import trade_view

app_name = 'trade'

urlpatterns = [
    path('', trade_view, name="trade_index"),
]