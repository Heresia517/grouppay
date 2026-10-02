"""Signaux auto pour créer des notifications sur les changements de statut."""
from django.db.models.signals import post_save
from django.dispatch import receiver


TEMPLATES = {
    "VALIDEE":        ("Commande validée ✓",       "Votre commande {num} a été validée et sera bientôt livrée."),
    "REFUSEE":        ("Commande refusée",         "Votre commande {num} a été refusée. Motif : {reason}"),
    "EN_LIVRAISON":   ("Commande en route 🚚",     "Votre commande {num} est en cours de livraison."),
    "LIVREE":         ("Commande livrée 🎉",       "Votre commande {num} a été livrée. Merci !"),
    "ANNULEE":        ("Commande annulée",         "Votre commande {num} a été annulée."),
}


@receiver(post_save, sender="orders.OrderStatusHistory")
def notify_on_status_change(sender, instance, created, **kwargs):
    """Créé une Notification quand le statut d'une commande change."""
    if not created:
        return

    order = instance.order
    status = instance.to_status
    tpl = TEMPLATES.get(status)
    if not tpl:
        return

    title, body_tpl = tpl
    body = body_tpl.format(
        num=order.order_number,
        reason=(instance.comment or "Non précisé")[:200],
    )

    from apps.notifications.models import Notification
    notif = Notification.objects.create(
        organization=order.organization,
        recipient=order.member,
        channel="IN_APP",
        title=title,
        body=body,
        is_read=False,
    )

    # Push WebSocket si Channels dispo
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer
        layer = get_channel_layer()
        if layer is not None:
            async_to_sync(layer.group_send)(
                f"notif_{order.member.id}",
                {
                    "type": "notify",
                    "payload": {
                        "id": str(notif.id),
                        "title": title,
                        "body": body,
                        "created_at": notif.created_at.strftime("%d/%m %H:%M"),
                        "is_read": False,
                    },
                },
            )
    except Exception:
        pass



# ═══════════════════════════════════════════════════════════════
# EMAILS HTML sur changement de statut
# ═══════════════════════════════════════════════════════════════
@receiver(post_save, sender="orders.OrderStatusHistory")
def send_email_on_status_change(sender, instance, created, **kwargs):
    """Envoie un email HTML quand le statut change."""
    if not created:
        return
    from .email_service import send_order_validated_email, send_order_delivered_email

    status = instance.to_status
    order = instance.order

    try:
        if status == "VALIDEE":
            send_order_validated_email(order)
        elif status == "LIVREE":
            send_order_delivered_email(order)
    except Exception:
        pass



# ═══════════════════════════════════════════════════════════════
# SMS sur changement de statut
# ═══════════════════════════════════════════════════════════════
@receiver(post_save, sender="orders.OrderStatusHistory")
def send_sms_on_status_change(sender, instance, created, **kwargs):
    """Envoie un SMS court quand le statut change."""
    if not created:
        return

    from .sms_service import (
        send_order_validated_sms, send_order_delivered_sms, send_order_rejected_sms,
    )

    status = instance.to_status
    order = instance.order

    try:
        if status == "VALIDEE":
            send_order_validated_sms(order)
        elif status == "LIVREE":
            send_order_delivered_sms(order)
        elif status == "REFUSEE":
            send_order_rejected_sms(order, instance.comment or "")
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════
# Emails additionnels (REFUSEE, EN_LIVRAISON)
# ═══════════════════════════════════════════════════════════════
@receiver(post_save, sender="orders.OrderStatusHistory")
def send_extra_emails(sender, instance, created, **kwargs):
    if not created:
        return
    from .email_service import send_order_rejected_email, send_order_shipping_email

    status = instance.to_status
    order = instance.order
    try:
        if status == "REFUSEE":
            send_order_rejected_email(order, instance.comment or "")
        elif status == "EN_LIVRAISON":
            send_order_shipping_email(order)
    except Exception:
        pass
