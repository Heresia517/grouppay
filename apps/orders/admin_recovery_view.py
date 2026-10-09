"""Vues admin pour les relances de paniers."""
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Cart
from .cart_recovery import (
    get_abandoned_carts, send_cart_recovery, get_cart_recovery_stats,
    build_cart_recovery_email_context,
)


def _require_rh(user):
    if user.role not in ("ADMIN", "GESTIONNAIRE"):
        raise PermissionDenied("Reserve RH")


@login_required
def abandoned_carts_list(request):
    """Liste des paniers abandonnes."""
    _require_rh(request.user)
    org = request.user.organization

    # Filtre : min heures
    hours_min = int(request.GET.get("hours", "24"))
    hours_max = request.GET.get("max")
    hours_max = int(hours_max) if hours_max else None

    carts_qs = get_abandoned_carts(hours_min=hours_min, hours_max=hours_max)
    carts_qs = carts_qs.filter(user__organization=org)

    # Enrichir chaque cart
    carts_data = []
    for cart in carts_qs[:200]:
        ctx = build_cart_recovery_email_context(cart)
        carts_data.append({
            "cart": cart,
            "user": cart.user,
            "items_count": ctx["item_count"],
            "total": ctx["total"],
            "currency": ctx["currency"],
            "created_at": cart.created_at,
            "hours_ago": int((timezone.now() - cart.created_at).total_seconds() / 3600),
        })

    stats = get_cart_recovery_stats(days=30)

    return render(request, "mutuelle/abandoned_carts.html", {
        "carts_data": carts_data,
        "stats": stats,
        "hours_min": hours_min,
    })


@login_required
@require_POST
def cart_recovery_send(request, cart_id):
    """Envoie une relance manuelle."""
    _require_rh(request.user)
    cart = get_object_or_404(
        Cart, id=cart_id, user__organization=request.user.organization,
    )

    channel = request.POST.get("channel", "EMAIL")
    success, error = send_cart_recovery(cart, channel=channel)

    if success:
        messages.success(request, f"Relance envoyee a {cart.user.email}")
    else:
        messages.error(request, f"Echec : {error}")

    return redirect("abandoned_carts_list")


@login_required
@require_POST
def cart_recovery_send_all(request):
    """Envoie une relance a tous les paniers abandonnes."""
    _require_rh(request.user)
    org = request.user.organization

    carts = get_abandoned_carts(hours_min=24).filter(user__organization=org)

    sent = 0
    failed = 0
    for cart in carts[:100]:
        success, _ = send_cart_recovery(cart, channel="EMAIL")
        if success:
            sent += 1
        else:
            failed += 1

    messages.success(request, f"Relances envoyees : {sent} OK, {failed} echecs")
    return redirect("abandoned_carts_list")
