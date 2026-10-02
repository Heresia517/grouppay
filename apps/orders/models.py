import uuid
from django.db import models
from apps.organizations.models import Organization
from apps.catalog.models import Product


class Cart(models.Model):
    STATUS_CHOICES = [("OPEN", "Open"), ("LOCKED", "Locked"), ("EXPIRED", "Expired")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField("accounts.User", on_delete=models.CASCADE, related_name="cart")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="OPEN")
    coupon_code = models.CharField(max_length=30, blank=True)
    coupon_discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)


class CartItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["cart", "product"], name="unique_product_per_cart"),
        ]


class Order(models.Model):
    STATUS_CHOICES = [
        ("EN_ATTENTE_VALIDATION", "En attente de validation"),
        ("VALIDEE", "Validée"),
        ("REFUSEE", "Refusée"),
        ("EN_PREPARATION", "En préparation"),
        ("PRETE_LIVRAISON", "Prête pour livraison"),
        ("EN_LIVRAISON", "En livraison"),
        ("LIVREE", "Livrée"),
        ("ANNULEE", "Annulée"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="orders")
    order_number = models.CharField(max_length=30, unique=True)
    member = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="orders")
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default="EN_ATTENTE_VALIDATION")
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency_code = models.CharField(max_length=3)
    delivery_address = models.TextField()
    rejection_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class OrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)


class OrderStatusHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="status_history")
    from_status = models.CharField(max_length=25, blank=True)
    to_status = models.CharField(max_length=25)
    actor = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
