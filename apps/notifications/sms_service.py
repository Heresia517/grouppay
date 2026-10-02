"""Service SMS — Africa's Talking avec fallback console."""
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def send_sms(phone, message):
    """Envoie un SMS. Fallback console si pas de config."""
    if not phone:
        return False

    try:
        username = getattr(settings, "AFRICASTALKING_USERNAME", "")
        api_key = getattr(settings, "AFRICASTALKING_API_KEY", "")

        if username and api_key:
            import africastalking
            africastalking.initialize(username, api_key)
            sms = africastalking.SMS
            response = sms.send(message, [phone])
            logger.info(f"[SMS] Sent to {phone}: {response}")
            return True
        else:
            # Console fallback (dev)
            print(f"\n📱 [SMS to {phone}]: {message}\n")
            return True
    except Exception as e:
        logger.warning(f"[SMS] Failed for {phone}: {e}")
        return False


def send_order_validated_sms(order):
    """SMS court : commande validée."""
    phone = getattr(order.member, "phone", "") or ""
    if not phone:
        return False
    msg = f"GroupPay: commande {order.order_number} VALIDEE ({order.total_amount} {order.currency_code})."
    return send_sms(phone, msg)


def send_order_delivered_sms(order):
    """SMS court : commande livrée."""
    phone = getattr(order.member, "phone", "") or ""
    if not phone:
        return False
    msg = f"GroupPay: commande {order.order_number} LIVREE. Merci !"
    return send_sms(phone, msg)


def send_order_rejected_sms(order, reason=""):
    """SMS court : commande refusée."""
    phone = getattr(order.member, "phone", "") or ""
    if not phone:
        return False
    msg = f"GroupPay: commande {order.order_number} REFUSEE. Motif: {reason[:80]}"
    return send_sms(phone, msg)
