import pytest
from decimal import Decimal


@pytest.fixture
def org(db):
    from apps.organizations.models import Organization
    return Organization.objects.create(name="SONABEL", slug="sonabel", currency_code="XOF")


@pytest.fixture
def member(db, org):
    from apps.accounts.models import User
    return User.objects.create_user(email="membre@sonabel.bf", organization=org, role="MEMBRE")


@pytest.fixture
def rh(db, org):
    from apps.accounts.models import User
    return User.objects.create_user(email="rh@sonabel.bf", organization=org, role="GESTIONNAIRE")


@pytest.fixture
def courier(db, org):
    from apps.accounts.models import User
    return User.objects.create_user(email="livreur@sonabel.bf", organization=org, role="LIVREUR")


@pytest.fixture
def supplier(db, org):
    from apps.accounts.models import User
    return User.objects.create_user(email="fournisseur@sonabel.bf", organization=org, role="FOURNISSEUR")


@pytest.fixture
def category(db, org):
    from apps.catalog.models import Category
    return Category.objects.create(organization=org, name="Vivres", slug="vivres")


@pytest.fixture
def product(db, org, category, supplier):
    from apps.catalog.models import Product
    return Product.objects.create(
        organization=org, category=category, supplier=supplier,
        name="Sac de riz 50kg", price=Decimal("35000"), stock_quantity=100, reorder_level=10,
    )


@pytest.fixture
def validated_order(db, member, product):
    from apps.orders.models import Order
    return Order.objects.create(
        organization=member.organization, order_number="TEST-2026-000001",
        member=member, status="VALIDEE", total_amount=Decimal("35000"),
        currency_code="XOF", delivery_address="Ouagadougou",
    )


@pytest.fixture
def delivery(db, validated_order):
    from apps.deliveries.services import create_delivery_for_order
    return create_delivery_for_order(validated_order)
