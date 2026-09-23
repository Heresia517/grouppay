import pytest
from datetime import date, timedelta
from apps.organizations.models import Organization
from apps.catalog.models import Category, Product
from apps.orders.models import Cart, CartItem
from apps.orders.services import create_order_from_cart, validate_order
from apps.deductions.services import generate_export_batch
from apps.deductions.models import DeductionTransmission
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def export_setup(db):
    org = Organization.objects.create(name="Test Org3", slug="test-org3", country_code="BF")
    admin = User.objects.create_user(email="admin@test3.com", organization=org, password="Test1234!", role="ADMIN", internal_id="")
    supplier = User.objects.create_user(email="fournisseur@test3.com", organization=org, password="Test1234!", role="FOURNISSEUR")
    category = Category.objects.create(organization=org, name="Divers", slug="divers")
    product = Product.objects.create(organization=org, category=category, supplier=supplier, name="Vélo", price=80000, stock_quantity=10)

    orders = []
    for i in range(3):
        member = User.objects.create_user(
            email=f"membre{i}@test3.com", organization=org, password="Test1234!",
            role="MEMBRE", internal_id=f"MAT-{i:03d}",
        )
        cart = Cart.objects.create(user=member)
        CartItem.objects.create(cart=cart, product=product, quantity=1)
        order = create_order_from_cart(member, delivery_address="Ouaga")
        validate_order(order, actor=admin)
        orders.append(order)

    return {"org": org, "admin": admin, "orders": orders}


def test_export_batch_creates_csv_and_updates_status(export_setup):
    org, admin = export_setup["org"], export_setup["admin"]
    today = date.today()

    batch = generate_export_batch(
        organization=org,
        period_start=today - timedelta(days=1),
        period_end=today + timedelta(days=1),
        generated_by=admin,
    )

    assert batch is not None
    assert batch.row_count == 3
    assert DeductionTransmission.objects.filter(organization=org, status="ENVOYEE").count() == 3
    assert DeductionTransmission.objects.filter(organization=org, status="EN_ATTENTE").count() == 0

    batch.file.open("r")
    content = batch.file.read()
    batch.file.close()
    assert "MAT-000" in content
    assert "MAT-001" in content
    assert "80000" in content


def test_export_returns_none_when_nothing_pending(export_setup):
    org, admin = export_setup["org"], export_setup["admin"]
    today = date.today()
    generate_export_batch(org, today - timedelta(days=1), today + timedelta(days=1), admin)

    # Deuxième export sur la même période : plus rien EN_ATTENTE
    second_batch = generate_export_batch(org, today - timedelta(days=1), today + timedelta(days=1), admin)
    assert second_batch is None
