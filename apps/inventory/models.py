"""Modeles du module Inventaire general."""
import uuid
from datetime import date, timedelta

from django.db import models
from django.utils import timezone

from apps.organizations.models import Organization
from apps.core.models import TenantModel


class AssetCategory(TenantModel):
    """Categorie d'actif (Informatique, Mobilier, Vehicule, etc.)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="asset_categories")
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    depreciation_years = models.PositiveSmallIntegerField(default=5, help_text="Duree d'amortissement (annees)")
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "name"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "code"], name="unique_asset_category_code"),
        ]
        verbose_name = "Categorie d'actif"

    def __str__(self):
        return f"{self.code} - {self.name}"


class Asset(TenantModel):
    """Un actif de l'organisation (materiel, mobilier, vehicule, etc.)."""
    STATUS_CHOICES = [
        ("AVAILABLE", "Disponible"),
        ("ASSIGNED", "Attribue"),
        ("MAINTENANCE", "En maintenance"),
        ("RETIRED", "Retire"),
        ("LOST", "Perdu"),
        ("STOLEN", "Vole"),
    ]
    CONDITION_CHOICES = [
        ("NEW", "Neuf"),
        ("GOOD", "Bon etat"),
        ("FAIR", "Etat moyen"),
        ("POOR", "Mauvais etat"),
        ("BROKEN", "Hors service"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="assets")
    category = models.ForeignKey(AssetCategory, on_delete=models.PROTECT, related_name="assets")

    # Identification
    reference = models.CharField(max_length=50, unique=True, help_text="ID unique (ex: INV-INFO-000001)")
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    serial_number = models.CharField(max_length=100, blank=True)
    barcode = models.CharField(max_length=50, blank=True)
    brand = models.CharField(max_length=100, blank=True)
    model_name = models.CharField(max_length=100, blank=True)

    # Acquisition
    purchase_date = models.DateField(null=True, blank=True)
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    supplier = models.CharField(max_length=200, blank=True)
    invoice_reference = models.CharField(max_length=100, blank=True)
    warranty_end_date = models.DateField(null=True, blank=True)

    # Localisation & usage
    location = models.CharField(max_length=200, blank=True, help_text="Batiment, bureau, etc.")
    assigned_to = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="assigned_assets",
    )
    assigned_at = models.DateTimeField(null=True, blank=True)

    # Etat
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="AVAILABLE")
    condition = models.CharField(max_length=10, choices=CONDITION_CHOICES, default="NEW")
    last_maintenance = models.DateField(null=True, blank=True)
    next_maintenance = models.DateField(null=True, blank=True)
    maintenance_interval_months = models.PositiveSmallIntegerField(default=12)

    # Valeur
    current_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    depreciation_rate = models.DecimalField(max_digits=5, decimal_places=2, default=20.00, help_text="% par an")

    # Meta
    notes = models.TextField(blank=True)
    image = models.ImageField(upload_to="assets/", null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["organization", "category", "status"]),
        ]
        verbose_name = "Actif"

    def __str__(self):
        return f"{self.reference} - {self.name}"

    @property
    def age_months(self):
        if not self.purchase_date:
            return 0
        delta = date.today() - self.purchase_date
        return int(delta.days / 30.44)

    @property
    def computed_value(self):
        """Valeur calculee avec amortissement."""
        if not self.purchase_price or not self.purchase_date:
            return self.current_value or 0

        months = self.age_months
        years = months / 12
        depreciation = float(self.purchase_price) * (float(self.depreciation_rate) / 100) * years
        value = max(0, float(self.purchase_price) - depreciation)
        return value

    @property
    def needs_maintenance(self):
        if not self.next_maintenance:
            return False
        return date.today() >= self.next_maintenance

    @property
    def warranty_active(self):
        if not self.warranty_end_date:
            return False
        return date.today() <= self.warranty_end_date


class AssetAssignment(models.Model):
    """Historique d'attribution d'un actif."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="assignments")
    assigned_to = models.ForeignKey("accounts.User", on_delete=models.CASCADE)
    assigned_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL,
        null=True, related_name="assignments_made",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    returned_at = models.DateTimeField(null=True, blank=True)
    condition_at_assignment = models.CharField(max_length=10, blank=True)
    condition_at_return = models.CharField(max_length=10, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-assigned_at"]
        verbose_name = "Attribution d'actif"

    def __str__(self):
        return f"{self.asset.reference} -> {self.assigned_to.email}"

    @property
    def is_active(self):
        return self.returned_at is None


class MaintenanceRecord(models.Model):
    """Enregistrement de maintenance."""
    TYPE_CHOICES = [
        ("PREVENTIVE", "Preventive"),
        ("CORRECTIVE", "Corrective"),
        ("UPGRADE", "Mise a niveau"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="maintenance_records")
    type = models.CharField(max_length=15, choices=TYPE_CHOICES, default="PREVENTIVE")
    date = models.DateField(default=date.today)
    performed_by = models.CharField(max_length=200, blank=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    description = models.TextField(blank=True)
    next_maintenance_date = models.DateField(null=True, blank=True)
    performed_by_user = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]
        verbose_name = "Maintenance"

    def __str__(self):
        return f"{self.asset.reference} - {self.get_type_display()} - {self.date}"


class AssetMovement(models.Model):
    """Historique des mouvements (localisation, changement de statut)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="movements")
    from_location = models.CharField(max_length=200, blank=True)
    to_location = models.CharField(max_length=200, blank=True)
    from_status = models.CharField(max_length=15, blank=True)
    to_status = models.CharField(max_length=15, blank=True)
    actor = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True)
    reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Mouvement d'actif"

    def __str__(self):
        return f"{self.asset.reference} - {self.created_at.strftime('%d/%m/%Y')}"
