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

    # Gestion fournisseur
    is_supplier_private = models.BooleanField(
        default=False,
        help_text="Produit visible uniquement par son fournisseur (brouillon)",
    )
    supplier_reference = models.CharField(
        max_length=50, blank=True,
        help_text="Référence interne du fournisseur",
    )

    # Gestion fournisseur
    is_supplier_private = models.BooleanField(
        default=False,
        help_text="Produit visible uniquement par son fournisseur (brouillon)",
    )
    supplier_reference = models.CharField(
        max_length=50, blank=True,
        help_text="Référence interne du fournisseur",
    )
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

    @property
    def average_rating(self):
        """Note moyenne (0 si aucun avis)."""
        from django.db.models import Avg
        result = self.reviews.filter(is_published=True).aggregate(avg=Avg("rating"))
        return round(result["avg"] or 0, 1)

    @property
    def review_count(self):
        """Nombre d'avis publiés."""
        return self.reviews.filter(is_published=True).count()

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



class Review(TenantModel):
    """Avis produit (5 étoiles + commentaire). Un membre ne peut reviewer
    qu'un produit qu'il a commandé et reçu."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="reviews")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    member = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="reviews")
    order = models.ForeignKey(
        "orders.Order", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="product_reviews",
    )
    rating = models.PositiveSmallIntegerField(
        choices=[(i, str(i)) for i in range(1, 6)],
    )
    title = models.CharField(max_length=120, blank=True)
    comment = models.TextField(blank=True)

    is_verified_purchase = models.BooleanField(default=False)
    is_published = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["product", "member"], name="unique_review_per_member_product"),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.product.name} — {self.rating}★ by {self.member.email}"



class StockMovement(TenantModel):
    """Historique de tous les mouvements de stock (traçabilité)."""
    TYPE_CHOICES = [
        ("IN", "Entrée"),
        ("OUT", "Sortie (commande)"),
        ("ADJUST", "Ajustement manuel"),
        ("RESTORE", "Restauration (refus)"),
        ("RETURN", "Retour client"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="stock_movements")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="movements")
    movement_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    quantity = models.IntegerField(help_text="Positif = entrée, négatif = sortie")
    stock_before = models.PositiveIntegerField()
    stock_after = models.PositiveIntegerField()
    reason = models.CharField(max_length=200, blank=True)
    order = models.ForeignKey(
        "orders.Order", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="stock_movements",
    )
    actor = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="stock_movements",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["product", "-created_at"]),
            models.Index(fields=["organization", "-created_at"]),
        ]

    def __str__(self):
        sign = "+" if self.quantity > 0 else ""
        return f"{self.product.name} : {sign}{self.quantity} ({self.movement_type})"


class StockAlert(TenantModel):
    """Alerte seuil stock critique (créée une fois par franchissement)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="stock_alerts")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="alerts")
    stock_at_alert = models.PositiveIntegerField()
    reorder_level = models.PositiveIntegerField()
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"ALERTE {self.product.name} ({self.stock_at_alert}/{self.reorder_level})"



class ProductRequest(TenantModel):
    """Proposition de produit à négocier en achat groupé (wishlist collaborative)."""
    STATUS_CHOICES = [
        ("OPEN", "Ouverte aux votes"),
        ("REVIEWING", "En négociation"),
        ("ACCEPTED", "Acceptée"),
        ("REJECTED", "Refusée"),
        ("ARCHIVED", "Archivée"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="product_requests")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category_hint = models.CharField(max_length=100, blank=True, help_text="Catégorie suggérée")
    target_price = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Prix cible souhaité",
    )
    proposed_by = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="product_requests",
    )
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="OPEN")
    reviewed_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reviewed_requests",
    )
    review_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status", "-created_at"]),
        ]

    def __str__(self):
        return self.title

    @property
    def vote_count(self):
        return self.votes.count()

    @property
    def has_voted(self):
        return False  # définir via annotate dans la vue


class ProductRequestVote(TenantModel):
    """Vote d'un membre sur une proposition."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="product_request_votes")
    request = models.ForeignKey(ProductRequest, on_delete=models.CASCADE, related_name="votes")
    member = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="product_request_votes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["request", "member"], name="unique_vote_per_member_request"),
        ]

    def __str__(self):
        return f"{self.member.email} vote pour {self.request.title}"
