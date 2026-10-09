"""Service de conversion de devises."""
from decimal import Decimal, ROUND_HALF_UP

from django.core.cache import cache


# Taux par defaut (fallback si pas en base)
DEFAULT_RATES = {
    ("XOF", "EUR"): Decimal("0.001524"),
    ("EUR", "XOF"): Decimal("655.957"),
    ("XOF", "USD"): Decimal("0.001667"),
    ("USD", "XOF"): Decimal("600.00"),
    ("EUR", "USD"): Decimal("1.09"),
    ("USD", "EUR"): Decimal("0.917"),
}


def get_exchange_rate(from_currency, to_currency):
    """Recupere le taux de change."""
    if from_currency == to_currency:
        return Decimal("1")

    cache_key = f"fx:{from_currency}:{to_currency}"
    cached = cache.get(cache_key)
    if cached:
        return Decimal(str(cached))

    try:
        from .models import ExchangeRate
        rate_obj = ExchangeRate.objects.filter(
            from_currency=from_currency, to_currency=to_currency,
        ).first()
        if rate_obj:
            cache.set(cache_key, str(rate_obj.rate), 3600)
            return rate_obj.rate
    except Exception:
        pass

    # Fallback
    rate = DEFAULT_RATES.get((from_currency, to_currency))
    if rate:
        cache.set(cache_key, str(rate), 3600)
        return rate

    # Essayer via USD intermediaire
    if from_currency != "USD" and to_currency != "USD":
        try:
            r1 = get_exchange_rate(from_currency, "USD")
            r2 = get_exchange_rate("USD", to_currency)
            rate = r1 * r2
            cache.set(cache_key, str(rate), 3600)
            return rate
        except Exception:
            pass

    return None


def convert_amount(amount, from_currency, to_currency):
    """Convertit un montant d'une devise a l'autre."""
    if from_currency == to_currency:
        return Decimal(str(amount)), Decimal("1")

    rate = get_exchange_rate(from_currency, to_currency)
    if not rate:
        return None, None

    converted = (Decimal(str(amount)) * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return converted, rate


def format_currency(amount, currency_code):
    """Formate un montant avec son symbole."""
    symbols = {"XOF": "FCFA", "EUR": "€", "USD": "$"}
    symbol = symbols.get(currency_code, currency_code)

    try:
        amount_float = float(amount)
        if currency_code == "XOF":
            return f"{amount_float:,.0f} {symbol}".replace(",", " ")
        return f"{amount_float:,.2f} {symbol}".replace(",", " ")
    except Exception:
        return f"{amount} {symbol}"


def seed_default_currencies():
    """Initialise les devises par defaut."""
    from .models import Currency, ExchangeRate

    currencies = [
        ("XOF", "Franc CFA (BCEAO)", "FCFA", 0),
        ("EUR", "Euro", "€", 2),
        ("USD", "Dollar americain", "$", 2),
    ]
    for code, name, symbol, decimals in currencies:
        Currency.objects.update_or_create(
            code=code,
            defaults={"name": name, "symbol": symbol, "decimal_places": decimals},
        )

    for (frm, to), rate in DEFAULT_RATES.items():
        ExchangeRate.objects.update_or_create(
            from_currency=frm, to_currency=to,
            defaults={"rate": rate, "source": "default"},
        )

    return {
        "currencies": Currency.objects.count(),
        "rates": ExchangeRate.objects.count(),
    }
