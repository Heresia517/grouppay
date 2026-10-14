"""Filtres template pour le FCFA."""
from django import template
from django.template.defaultfilters import floatformat

register = template.Library()


@register.filter
def fcfa(value):
    """Formate un montant en FCFA avec séparateurs."""
    if value is None:
        return "—"
    try:
        v = int(float(value))
        return f"{v:,}".replace(",", " ") + " FCFA"
    except (ValueError, TypeError):
        return str(value)


@register.filter
def fcfa_short(value):
    """Formate en FCFA court : 1,2 M / 450 k."""
    if value is None:
        return "—"
    try:
        v = float(value)
        if v >= 1_000_000:
            return f"{v/1_000_000:.1f} M FCFA"
        if v >= 1_000:
            return f"{v/1_000:.0f} k FCFA"
        return f"{int(v)} FCFA"
    except (ValueError, TypeError):
        return str(value)
