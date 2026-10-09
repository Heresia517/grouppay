"""Vues multi-devises."""
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render

from .currency_service import convert_amount, get_exchange_rate
from .models import Currency, ExchangeRate


@login_required
def currency_converter(request):
    """Page convertisseur de devises."""
    currencies = Currency.objects.filter(is_active=True)
    rates = ExchangeRate.objects.all().order_by("from_currency", "to_currency")

    return render(request, "mutuelle/currency_converter.html", {
        "currencies": currencies,
        "rates": rates,
    })


@login_required
def api_convert(request):
    """API conversion AJAX."""
    try:
        amount = Decimal(request.GET.get("amount", "0"))
        from_currency = request.GET.get("from", "XOF").upper()
        to_currency = request.GET.get("to", "EUR").upper()

        converted, rate = convert_amount(amount, from_currency, to_currency)
        if converted is None:
            return JsonResponse({"error": "Taux indisponible"}, status=400)

        return JsonResponse({
            "amount": float(amount),
            "from": from_currency,
            "to": to_currency,
            "converted": float(converted),
            "rate": float(rate),
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)
