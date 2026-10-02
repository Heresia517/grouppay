"""
Services métier livraisons.

Couvre :
- RG-16 : création auto de la livraison après validation commande
- RG-17 : assignation du livreur (self-claim ou admin)
- RG-18 : preuve de livraison (photo ou signature)
- RG-19 : statut LIVREE clôture la commande
- RG-20 : max 3 tentatives puis ECHEC
"""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone


MAX_DELIVERY_ATTEMPTS = 3


class DeliveryError(Exception):
    """Erreur métier générique."""


class InvalidDeliveryStatusError(DeliveryError):
    pass


class MaxAttemptsReachedError(DeliveryError):
    pass


@transaction.atomic
def create_delivery_for_order(order, courier=None):
    """RG-16 : crée une Delivery pour une commande validée. Idempotent."""
    from .models import Delivery
    from apps.orders.models import OrderStatusHistory

    existing = Delivery.objects.filter(order=order).first()
    if existing:
        return existing

    if order.status not in ("VALIDEE", "EN_PREPARATION", "PRETE_LIVRAISON"):
        raise InvalidDeliveryStatusError(
            f"Impossible de créer une livraison pour une commande {order.status}"
        )

    delivery = Delivery.objects.create(
        order=order,
        courier=courier,
        status="AFFECTEE" if courier else "CREEE",
    )

    old_status = order.status
    order.status = "EN_LIVRAISON"
    order.save(update_fields=["status"])

    OrderStatusHistory.objects.create(
        order=order,
        from_status=old_status,
        to_status="EN_LIVRAISON",
        actor=courier,
        comment="Livraison créée",
    )
    return delivery


@transaction.atomic
def assign_courier(delivery, courier):
    """RG-17 : assigne un livreur (self-claim ou admin)."""
    if delivery.status in ("LIVREE", "PERDUE", "RETOURNEE", "ECHEC"):
        raise InvalidDeliveryStatusError(
            f"Impossible de réassigner une livraison {delivery.status}"
        )
    delivery.courier = courier
    delivery.status = "AFFECTEE"
    delivery.save(update_fields=["courier", "status"])
    return delivery


@transaction.atomic
def mark_delivered(delivery, proof_data=None, actor=None):
    """
    RG-18 : preuve obligatoire (photo OU signature) sauf skip_proof=True.
    RG-19 : clôture la commande (LIVREE) + audit.
    Accepte CREEE → LIVREE (livraison directe sans étape intermédiaire).
    """
    from apps.orders.models import OrderStatusHistory

    if delivery.status == "LIVREE":
        return delivery

    # Accepte : CREEE, AFFECTEE, EN_ROUTE, EN_COURS
    if delivery.status not in ("CREEE", "AFFECTEE", "EN_ROUTE", "EN_COURS"):
        raise InvalidDeliveryStatusError(
            f"Impossible de marquer livrée une livraison {delivery.status}"
        )

    proof_data = proof_data or {}
    has_proof = bool(proof_data.get("delivery_photo") or proof_data.get("signature_image"))
    if not has_proof and not proof_data.get("skip_proof"):
        raise ValidationError("Preuve de livraison requise (photo ou signature).")

    delivery.status = "LIVREE"
    delivery.delivered_at = timezone.now()
    if proof_data.get("delivery_photo"):
        delivery.delivery_photo = proof_data["delivery_photo"]
    if proof_data.get("signature_image"):
        delivery.signature_image = proof_data["signature_image"]
    delivery.save()

    order = delivery.order
    old_status = order.status
    order.status = "LIVREE"
    order.save(update_fields=["status"])

    OrderStatusHistory.objects.create(
        order=order,
        from_status=old_status,
        to_status="LIVREE",
        actor=actor or delivery.courier,
        comment="Livraison confirmée",
    )
    return delivery


def attempt_delivery(delivery, success, reason=None, actor=None):
    """
    RG-20 : incrémente attempts. Après 3 échecs → ECHEC.
    PAS de @transaction.atomic ici — sinon le save ECHEC est rollback
    quand MaxAttemptsReachedError est levée.
    """
    if delivery.status == "LIVREE":
        raise InvalidDeliveryStatusError("Livraison déjà effectuée.")

    if success:
        return mark_delivered(delivery, proof_data={"skip_proof": True}, actor=actor)

    delivery.attempts = (delivery.attempts or 0) + 1
    delivery.last_attempt_at = timezone.now()
    if reason:
        delivery.failure_reason = reason

    if delivery.attempts >= MAX_DELIVERY_ATTEMPTS:
        delivery.status = "ECHEC"
        delivery.save(update_fields=[
            "attempts", "last_attempt_at", "failure_reason", "status"
        ])
        raise MaxAttemptsReachedError(
            f"Livraison {delivery.id} : {MAX_DELIVERY_ATTEMPTS} tentatives échouées."
        )

    delivery.save(update_fields=["attempts", "last_attempt_at", "failure_reason"])
    return delivery


@transaction.atomic
def mark_returned(delivery, reason=None):
    """Marque une livraison comme retournée."""
    if delivery.status == "LIVREE":
        raise InvalidDeliveryStatusError("Livraison déjà effectuée.")
    delivery.status = "RETOURNEE"
    if reason:
        delivery.failure_reason = reason
    delivery.save(update_fields=["status", "failure_reason"])
    return delivery
