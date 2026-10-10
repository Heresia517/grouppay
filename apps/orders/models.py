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



class MonthlyReport(models.Model):
    """Rapport mensuel genere automatiquement."""
    STATUS_CHOICES = [
        ("PENDING", "En attente"),
        ("GENERATING", "Generation en cours"),
        ("READY", "Pret"),
        ("FAILED", "Echec"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE,
        related_name="monthly_reports",
    )
    year = models.PositiveIntegerField()
    month = models.PositiveIntegerField()

    # Fichiers generes
    pdf_file = models.FileField(upload_to="reports/", null=True, blank=True)
    excel_file = models.FileField(upload_to="reports/", null=True, blank=True)

    # Metriques snapshot
    orders_count = models.PositiveIntegerField(default=0)
    orders_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    da_count = models.PositiveIntegerField(default=0)
    da_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    members_active = models.PositiveIntegerField(default=0)

    # Meta
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="PENDING")
    generated_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    sent_to = models.JSONField(default=list, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-year", "-month"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "year", "month"],
                name="unique_monthly_report_per_org",
            ),
        ]
        verbose_name = "Rapport mensuel"

    def __str__(self):
        return f"Rapport {self.month:02d}/{self.year} - {self.organization.name}"

    @property
    def period_label(self):
        months = ["", "Janvier", "Fevrier", "Mars", "Avril", "Mai", "Juin",
                  "Juillet", "Aout", "Septembre", "Octobre", "Novembre", "Decembre"]
        return f"{months[self.month]} {self.year}"
