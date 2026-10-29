"""Service de relance des paniers abandonnes."""
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone

from .models import Cart, CartItem


def get_abandoned_carts(hours_min=24, hours_max=None):
    """Retourne les paniers abandonnes.

    Un panier est considere abandonne s'il est :
    - En statut OPEN
    - Cree il y a plus de hours_min heures
    - Contient au moins 1 article
    - N'a pas ete relance recemment
    """
    now = timezone.now()
    min_time = now - timedelta(hours=hours_min)

    qs = Cart.objects.filter(
        status="OPEN",
        created_at__lt=min_time,
        items__isnull=False,
    ).distinct().select_related("user", "user__organization")

    if hours_max:
        max_time = now - timedelta(hours=hours_max)
        qs = qs.filter(created_at__gt=max_time)

    return qs


def build_cart_recovery_email_context(cart):
    """Contexte pour l'email de relance."""
    org = cart.user.organization
    base_url = getattr(settings, "SITE_URL", "http://127.0.0.1:8000")

    items = cart.items.select_related("product").all()
    items_list = [
        {
            "name": item.product.name,
            "quantity": item.quantity,
            "price": float(item.product.price),
            "subtotal": float(item.product.price * item.quantity),
        }
        for item in items
    ]

    total = sum(i["subtotal"] for i in items_list)
    currency = org.currency_code

    return {
        "organization": org,
        "color_primary": org.color_primary,
        "color_secondary": org.color_secondary,
        "member_email": cart.user.email,
        "cart_url": f"{base_url}/cart/",
        "items": items_list,
        "total": total,
        "currency": currency,
        "item_count": len(items_list),
    }


def send_cart_recovery(cart, channel="EMAIL"):
    """Envoie une relance de panier abandonne."""
    user = cart.user
    context = build_cart_recovery_email_context(cart)

    if channel == "EMAIL":
        if not user.email:
            return False, "Pas d'email"
        try:
            from apps.notifications.email_service import send_email
            send_email(
                recipient_email=user.email,
                subject=f"🛒 Votre panier vous attend ({context['item_count']} articles)",
                template_name="emails/cart_recovery.html",
                context=context,
            )
        except Exception as e:
            return False, str(e)

    elif channel == "SMS":
        if not user.phone:
            return False, "Pas de telephone"
        try:
            from apps.notifications.sms_service import send_sms
            message = (
                f"ZionPay: votre panier de {context['item_count']} articles "
                f"({context['total']:.0f} {context['currency']}) vous attend. "
                f"Commandez: {context['cart_url']}"
            )
            send_sms(user.phone, message)
        except Exception as e:
            return False, str(e)

    # Notification in-app
    try:
        from apps.notifications.models import Notification
        Notification.objects.create(
            organization=user.organization,
            recipient=user,
            channel="IN_APP",
            title="🛒 Votre panier vous attend",
            body=f"{context['item_count']} articles en attente ({context['total']:.0f} {context['currency']})",
        )
    except Exception:
        pass

    return True, None


def get_cart_recovery_stats(days=30):
    """Statistiques sur les relances."""
    now = timezone.now()
    start = now - timedelta(days=days)

    total_carts = Cart.objects.filter(
        status="OPEN",
        created_at__gte=start,
        items__isnull=False,
    ).distinct().count()

    abandoned = get_abandoned_carts(hours_min=24).count()

    # Paniers qui ont abouti (LOCKED)
    converted = Cart.objects.filter(
        status="LOCKED",
        created_at__gte=start,
    ).count()

    total = total_carts + converted
    conversion_rate = (converted / total * 100) if total else 0

    return {
        "active_carts": total_carts,
        "abandoned_carts": abandoned,
        "converted_carts": converted,
        "conversion_rate": round(conversion_rate, 1),
    }
