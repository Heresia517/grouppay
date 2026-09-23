import pytest
from apps.organizations.models import Organization
from apps.catalog.models import Category, Product
from apps.orders.models import Cart, CartItem, Order
from apps.orders.services import create_order_from_cart, InsufficientStockError
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def setup_data(db):
    org = Organization.objects.create(name="Test Org", slug="test-org", country_code="BF")
    supplier = User.objects.create_user(email="fournisseur@test.com", organization=org, password="Test1234!", role="FOURNISSEUR")
    member = User.objects.create_user(email="membre@test.com", organization=org, password="Test1234!", role="MEMBRE")
    category = Category.objects.create(organization=org, name="Électroménager", slug="electromenager")
    product = Product.objects.create(
        organization=org, category=category, supplier=supplier,
        name="Frigo", price=150000, stock_quantity=2,
    )
    return {"org": org, "member": member, "product": product}


def test_order_creation_decreases_stock(setup_data):
    member, product = setup_data["member"], setup_data["product"]
    cart = Cart.objects.create(user=member)
    CartItem.objects.create(cart=cart, product=product, quantity=2)

    order = create_order_from_cart(member, delivery_address="Ouaga, secteur 15")

    product.refresh_from_db()
    assert product.stock_quantity == 0
    assert order.status == "EN_ATTENTE_VALIDATION"
    assert order.total_amount == 300000
    assert order.items.count() == 1
    assert order.items.first().unit_price == 150000


def test_order_creation_fails_if_stock_insufficient(setup_data):
    member, product = setup_data["member"], setup_data["product"]
    cart = Cart.objects.create(user=member)
    CartItem.objects.create(cart=cart, product=product, quantity=5)  # stock = 2 seulement

    with pytest.raises(InsufficientStockError):
        create_order_from_cart(member, delivery_address="Ouaga, secteur 15")

    product.refresh_from_db()
    assert product.stock_quantity == 2  # inchangé — transaction annulée (RG-01)


def test_unit_price_frozen_after_product_price_change(setup_data):
    """RG-02 : le prix change après coup, la commande garde l'ancien prix."""
    member, product = setup_data["member"], setup_data["product"]
    cart = Cart.objects.create(user=member)
    CartItem.objects.create(cart=cart, product=product, quantity=1)

    order = create_order_from_cart(member, delivery_address="Ouaga, secteur 15")

    product.price = 200000
    product.save()

    order_item = order.items.first()
    assert order_item.unit_price == 150000  # toujours l'ancien prix
