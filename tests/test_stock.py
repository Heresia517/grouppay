import pytest
from apps.catalog.services import (
    decrement_stock, increment_stock, check_low_stock, InsufficientStockError,
)


@pytest.mark.django_db
def test_low_stock_alert_triggered(product):
    product.reorder_level = 10
    product.stock_quantity = 5
    product.save()
    low = check_low_stock(product.organization)
    assert any(p["id"] == product.id for p in low)


@pytest.mark.django_db
def test_negative_stock_forbidden(product):
    product.stock_quantity = 1
    product.save()
    with pytest.raises(InsufficientStockError):
        decrement_stock(product, 10)
    product.refresh_from_db()
    assert product.stock_quantity == 1


@pytest.mark.django_db
def test_decrement_increment_roundtrip(product):
    initial = product.stock_quantity
    decrement_stock(product, 3)
    increment_stock(product, 3)
    product.refresh_from_db()
    assert product.stock_quantity == initial
