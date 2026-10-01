from datetime import date
from django.db import transaction
from django.core.exceptions import ValidationError
from apps.catalog.models import Product
from .models import Cart, Order, OrderItem, OrderStatusHistory


class InsufficientStockError(Exception):
    pass


class EmptyCartError(Exception):
    pass


class InvalidOrderStatusError(Exception):
    pass


def generate_order_number(organization):
    year = date.today().year
    prefix = f"{organization.slug.upper()}-{year}-"
    count_this_year = Order.objects.filter(
        organization=organization, order_number__startswith=prefix
    ).count()
    return f"{prefix}{count_this_year + 1:06d}"


@transaction.atomic
def create_order_from_cart(user, delivery_address):
    """RG-01 : vérifie et verrouille le stock avant toute création.
    RG-02 : le prix unitaire est figé au moment de la commande."""
    try:
        cart = Cart.objects.select_for_update().get(user=user, status="OPEN")
    except Cart.DoesNotExist:
        raise EmptyCartError("Aucun panier ouvert pour cet utilisateur.")

    items = list(cart.items.select_related("product").all())
    if not items:
        raise EmptyCartError("Le panier est vide.")

    organization = user.organization
    order = Order.objects.create(
        organization=organization,
        order_number=generate_order_number(organization),
        member=user,
        total_amount=0,
        currency_code=organization.currency_code,
        delivery_address=delivery_address,
    )

    total = 0
    for item in items:
        product = Product.objects.select_for_update().get(pk=item.product.pk)

        if product.stock_quantity < item.quantity:
            raise InsufficientStockError(
                f"Stock insuffisant pour {product.name} "
                f"(demandé: {item.quantity}, disponible: {product.stock_quantity})"
            )

        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=item.quantity,
            unit_price=product.price,
        )
        product.stock_quantity -= item.quantity
        product.save(update_fields=["stock_quantity"])
        total += product.price * item.quantity

    order.total_amount = total
    order.save(update_fields=["total_amount"])

    OrderStatusHistory.objects.create(
        order=order, from_status="", to_status="EN_ATTENTE_VALIDATION", actor=user
    )

    cart.status = "LOCKED"
    cart.save(update_fields=["status"])

    return order


@transaction.atomic
def validate_order(order, actor):
    """RG-03 : la validation crée automatiquement une DeductionTransmission."""
    from apps.deductions.models import DeductionTransmission
    from apps.documents.services import generate_purchase_order_pdf
    from apps.notifications.models import Notification
    from apps.notifications.tasks import send_email_notification

    if order.status != "EN_ATTENTE_VALIDATION":
        raise InvalidOrderStatusError(f"Impossible de valider une commande au statut {order.status}")

    old_status = order.status
    order.status = "VALIDEE"
    order.save(update_fields=["status"])

    OrderStatusHistory.objects.create(
        order=order, from_status=old_status, to_status="VALIDEE", actor=actor
    )

    DeductionTransmission.objects.create(
        order=order,
        organization=order.organization,
        reference=f"DED-{order.order_number}",
        status="EN_ATTENTE",
    )

    # Génère le PDF
    try:
        generate_purchase_order_pdf(order)
    except:
        pass  # Si PDF échoue, ne pas bloquer la commande

    # Envoie notification
    notif = Notification.objects.create(
        organization=order.organization,
        recipient=order.member,
        channel="EMAIL",
        title=f"Votre commande {order.order_number} validée",
        body=f"Montant : {order.total_amount} {order.currency_code}",
    )
    try:
        send_email_notification.delay(notif.id)
    except:
        pass  # Celery optionnel

    return order


@transaction.atomic
def reject_order(order, actor, reason):
    """RG-04 : le refus restaure le stock exact des lignes de la commande."""
    from apps.notifications.models import Notification
    from apps.notifications.tasks import send_email_notification

    if order.status != "EN_ATTENTE_VALIDATION":
        raise InvalidOrderStatusError(f"Impossible de refuser une commande au statut {order.status}")

    if not reason:
        raise ValidationError("Le motif de refus est obligatoire.")

    old_status = order.status
    order.status = "REFUSEE"
    order.rejection_reason = reason
    order.save(update_fields=["status", "rejection_reason"])

    for item in order.items.select_related("product"):
        product = Product.objects.select_for_update().get(pk=item.product.pk)
        product.stock_quantity += item.quantity
        product.save(update_fields=["stock_quantity"])

    OrderStatusHistory.objects.create(
        order=order, from_status=old_status, to_status="REFUSEE", actor=actor, comment=reason
    )

    # Notification
    notif = Notification.objects.create(
        organization=order.organization,
        recipient=order.member,
        channel="EMAIL",
        title=f"Votre commande {order.order_number} refusée",
        body=f"Motif : {reason}",
    )
    try:
        send_email_notification.delay(notif.id)
    except:
        pass

    return order
