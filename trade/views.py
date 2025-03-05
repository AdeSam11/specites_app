from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def trade_view(request):
    return render(request, "trade/index.html")
