import uuid
from django.db import models
from django.utils import timezone
from apps.organizations.models import Organization
from apps.core.models import TenantModel


class Category(TenantModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="categories")
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100)
    description = models.TextField(blank=True)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="children")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization", "slug"], name="unique_category_slug_per_org"),
        ]

    def __str__(self):
        return self.name


class Product(TenantModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="products")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    supplier = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="products")

    sku = models.CharField(max_length=50, blank=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    tags = models.CharField(max_length=500, blank=True, help_text="CSV: promo,new,bulk")

    price = models.DecimalField(max_digits=12, decimal_places=2)
    compare_at_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    discount_percent = models.PositiveIntegerField(default=0)
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    stock_quantity = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=10)
    max_per_member = models.PositiveIntegerField(null=True, blank=True)

    weight_kg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    lead_time_days = models.PositiveIntegerField(null=True, blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(stock_quantity__gte=0),
                name="product_stock_non_negative",
            ),
        ]

    @property
    def is_available(self):
        return self.stock_quantity > 0 and self.is_active

    def __str__(self):
        return self.name


class ProductVariant(TenantModel):
    """Variations produit (taille, couleur, etc.). RG-23 : stock variant prioritaire."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="product_variants")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    sku = models.CharField(max_length=50, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    stock_quantity = models.PositiveIntegerField(default=0)
    attributes = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.product.name} — {self.attributes}"



class Coupon(TenantModel):
    """Code promo applicable au panier."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="coupons")
    code = models.CharField(max_length=30, db_index=True)
    description = models.CharField(max_length=200, blank=True)
    discount_type = models.CharField(
        max_length=10,
        choices=[("percent", "Pourcentage"), ("fixed", "Montant fixe")],
        default="percent",
    )
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    min_order_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    max_uses = models.PositiveIntegerField(null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)
    valid_from = models.DateTimeField(default=timezone.now)
    valid_to = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization", "code"], name="unique_coupon_code_per_org"),
        ]

    def __str__(self):
        return self.code

    @property
    def is_valid(self):
        now = timezone.now()
        if not self.is_active: return False
        if self.valid_from and self.valid_from > now: return False
        if self.valid_to and self.valid_to < now: return False
        if self.max_uses is not None and self.used_count >= self.max_uses: return False
        return True

    def compute_discount(self, amount):
        from decimal import Decimal
        amount = Decimal(str(amount))
        if amount < self.min_order_amount:
            return Decimal("0")
        if self.discount_type == "percent":
            return (amount * self.discount_value / 100).quantize(Decimal("0.01"))
        return min(self.discount_value, amount)


class WishlistItem(TenantModel):
    """Produit sauvegardé par un membre."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="wishlist_items")
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="wishlist")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="wishlisted_by")
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "product"], name="unique_wishlist_item")]
        ordering = ["-added_at"]

    def __str__(self):
        return f"{self.user.email} love {self.product.name}"
