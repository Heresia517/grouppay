import pytest
from django.core.exceptions import ValidationError
from apps.deliveries.services import (
    create_delivery_for_order, mark_delivered, attempt_delivery,
    MaxAttemptsReachedError, MAX_DELIVERY_ATTEMPTS,
)


@pytest.mark.django_db
def test_delivery_created_on_validation(validated_order):
    d = create_delivery_for_order(validated_order)
    assert d.status == "CREEE"
    validated_order.refresh_from_db()
    assert validated_order.status == "EN_LIVRAISON"


@pytest.mark.django_db
def test_delivery_retry_limit_3(delivery):
    for _ in range(MAX_DELIVERY_ATTEMPTS - 1):
        attempt_delivery(delivery, success=False, reason="absent")
    with pytest.raises(MaxAttemptsReachedError):
        attempt_delivery(delivery, success=False, reason="absent")
    delivery.refresh_from_db()
    assert delivery.status == "ECHEC"
    assert delivery.attempts == MAX_DELIVERY_ATTEMPTS


@pytest.mark.django_db
def test_delivered_closes_order(delivery):
    mark_delivered(delivery, proof_data={"skip_proof": True})
    delivery.order.refresh_from_db()
    assert delivery.order.status == "LIVREE"
    assert delivery.status == "LIVREE"


@pytest.mark.django_db
def test_proof_of_delivery_required(delivery):
    with pytest.raises(ValidationError):
        mark_delivered(delivery, proof_data={})
