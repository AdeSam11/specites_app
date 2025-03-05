from django.urls import path
from .views import invest_view, investment_history, portfolio_view

app_name = "investment"

urlpatterns = [
    path("", invest_view, name="invest"),
    path("history/", investment_history, name="investment_history"),
    path("portfolio/", portfolio_view, name="portfolio"),
]
