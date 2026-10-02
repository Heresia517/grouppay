"""Service d'envoi d'emails HTML."""
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def send_email(recipient_email, subject, template_name, context):
    """Envoie un email HTML à partir d'un template."""
    try:
        html = render_to_string(template_name, context)
        text = strip_tags(html)
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "GroupPay <noreply@grouppay.app>")
        msg = EmailMultiAlternatives(subject, text, from_email, [recipient_email])
        msg.attach_alternative(html, "text/html")
        msg.send(fail_silently=True)
        return True
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Email send failed: {e}")
        return False


def send_order_validated_email(order):
    from django.conf import settings
    base_url = getattr(settings, "SITE_URL", "http://127.0.0.1:8000")
    return send_email(
        recipient_email=order.member.email,
        subject=f"✓ Commande {order.order_number} validée",
        template_name="emails/order_validated.html",
        context={
            "organization": order.organization,
            "color_primary": order.organization.color_primary,
            "color_secondary": order.organization.color_secondary,
            "order_number": order.order_number,
            "total_amount": f"{order.total_amount:,.0f}".replace(",", " "),
            "currency": order.currency_code,
            "order_url": f"{base_url}/orders/{order.id}/",
        },
    )


def send_order_delivered_email(order):
    from django.conf import settings
    base_url = getattr(settings, "SITE_URL", "http://127.0.0.1:8000")
    return send_email(
        recipient_email=order.member.email,
        subject=f"🎉 Commande {order.order_number} livrée",
        template_name="emails/order_delivered.html",
        context={
            "organization": order.organization,
            "order_number": order.order_number,
            "order_url": f"{base_url}/orders/{order.id}/",
        },
    )



def send_order_rejected_email(order, reason=""):
    from django.conf import settings
    base_url = getattr(settings, "SITE_URL", "http://127.0.0.1:8000")
    return send_email(
        recipient_email=order.member.email,
        subject=f"Commande {order.order_number} refusée",
        template_name="emails/order_rejected.html",
        context={
            "organization": order.organization,
            "order_number": order.order_number,
            "reason": reason or "Non précisé",
            "order_url": f"{base_url}/orders/{order.id}/",
        },
    )


def send_order_shipping_email(order):
    from django.conf import settings
    base_url = getattr(settings, "SITE_URL", "http://127.0.0.1:8000")
    return send_email(
        recipient_email=order.member.email,
        subject=f"🚚 Commande {order.order_number} en livraison",
        template_name="emails/order_shipping.html",
        context={
            "organization": order.organization,
            "order_number": order.order_number,
            "order_url": f"{base_url}/orders/{order.id}/",
        },
    )
