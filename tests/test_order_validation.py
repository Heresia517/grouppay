import pytest
from apps.organizations.models import Organization
from apps.catalog.models import Category, Product
from apps.orders.models import Cart, CartItem
from apps.orders.services import create_order_from_cart, validate_order, reject_order
from apps.deductions.models import DeductionTransmission
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def order_setup(db):
    org = Organization.objects.create(name="Test Org2", slug="test-org2", country_code="BF")
    admin = User.objects.create_user(
        email="admin@test2.com", organization=org, password="Test1234!", role="ADMIN"
    )
    supplier = User.objects.create_user(
        email="fournisseur@test2.com", organization=org, password="Test1234!", role="FOURNISSEUR"
    )
    member = User.objects.create_user(
        email="membre@test2.com", organization=org, password="Test1234!", role="MEMBRE"
    )
    category = Category.objects.create(organization=org, name="Vivres", slug="vivres")
    product = Product.objects.create(
        organization=org,
        category=category,
        supplier=supplier,
        name="Sac de riz 50kg",
        price=25000,
        stock_quantity=10,
    )
    cart = Cart.objects.create(user=member)
    CartItem.objects.create(cart=cart, product=product, quantity=3)
    order = create_order_from_cart(member, delivery_address="Ouaga")

    # 🔧 Synchronise l'instance Python avec la DB.
    # Sans ça, product.stock_quantity vaut encore 10 (valeur du create),
    # alors que le service create_order_from_cart a écrit 7 en base.
    product.refresh_from_db()

    return {"order": order, "admin": admin, "product": product}


def test_validate_order_creates_deduction_transmission(order_setup):
    order, admin = order_setup["order"], order_setup["admin"]

    validated = validate_order(order, actor=admin)

    assert validated.status == "VALIDEE"
    transmission = DeductionTransmission.objects.get(order=order)
    assert transmission.status == "EN_ATTENTE"
    assert transmission.reference == f"DED-{order.order_number}"
    assert order.status_history.filter(to_status="VALIDEE").exists()


def test_reject_order_restores_stock(order_setup):
    order, admin, product = order_setup["order"], order_setup["admin"], order_setup["product"]
    stock_before = product.stock_quantity  # 10 - 3 = 7 après la commande ✅

    rejected = reject_order(order, actor=admin, reason="Rupture fournisseur")

    product.refresh_from_db()
    assert rejected.status == "REFUSEE"
    assert rejected.rejection_reason == "Rupture fournisseur"
    assert product.stock_quantity == stock_before + 3  # 7 + 3 = 10 (RG-04) ✅
    assert not DeductionTransmission.objects.filter(order=order).exists()


def test_cannot_validate_already_validated_order(order_setup):
    order, admin = order_setup["order"], order_setup["admin"]
    validate_order(order, actor=admin)

    from apps.orders.services import InvalidOrderStatusError

    with pytest.raises(InvalidOrderStatusError):
        validate_order(order, actor=admin)