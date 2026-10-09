"""Modeles du module Demande d'Achat (DA) + Signature numerique."""
import uuid
from datetime import date

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.organizations.models import Organization
from apps.core.models import TenantModel


# ═══════════════════════════════════════════════════════════════
# CATEGORIE D'ARTICLE
# ═══════════════════════════════════════════════════════════════
class DACategory(TenantModel):
    """Categorie d'article de fourniture."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="da_categories")
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "name"]
        verbose_name = "Categorie DA"

    def __str__(self):
        return self.name


# ═══════════════════════════════════════════════════════════════
# ARTICLE INTERNE (catalogue magasin)
# ═══════════════════════════════════════════════════════════════
class DAItem(TenantModel):
    """Article de fourniture interne (catalogue magasin)."""
    UNIT_CHOICES = [
        ("PCS", "Piece(s)"),
        ("BOX", "Boite(s)"),
        ("REAM", "Rame(s)"),
        ("PACK", "Paquet(s)"),
        ("KG", "Kilogramme(s)"),
        ("L", "Litre(s)"),
        ("M", "Metre(s)"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="da_items")
    category = models.ForeignKey(DACategory, on_delete=models.PROTECT, related_name="items")
    reference = models.CharField(max_length=50, blank=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default="PCS")
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    stock_quantity = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=5)
    max_per_request = models.PositiveIntegerField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_available_to_all = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category__display_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "reference"],
                condition=~models.Q(reference=""),
                name="unique_da_item_reference_per_org",
            ),
        ]
        verbose_name = "Article DA"

    def __str__(self):
        return f"{self.name} ({self.unit})"

    @property
    def is_low_stock(self):
        return self.stock_quantity <= self.reorder_level

    @property
    def is_out_of_stock(self):
        return self.stock_quantity == 0


# ═══════════════════════════════════════════════════════════════
# DEMANDE D'ACHAT
# ═══════════════════════════════════════════════════════════════
class PurchaseRequest(TenantModel):
    """Demande d'achat (DA)."""
    STATUS_CHOICES = [
        ("BROUILLON", "Brouillon"),
        ("SOUMISE", "Soumise"),
        ("VISEE_DIRECTEUR", "Visee par Directeur"),
        ("VISEE_CHEF", "Visee par Chef de service"),
        ("STOCK_VERIFIE", "Stock verifie par Achats"),
        ("VALIDEE", "Validee"),
        ("REFUSEE", "Refusee"),
        ("COMMANDEE", "Commandee"),
        ("RECUE_PARTIELLE", "Recue partiellement"),
        ("RECUE", "Recue"),
        ("CLOTUREE", "Cloturee"),
        ("ANNULEE", "Annulee"),
    ]

    PRIORITY_CHOICES = [
        ("BASSE", "Basse"),
        ("NORMALE", "Normale"),
        ("HAUTE", "Haute"),
        ("URGENTE", "Urgente"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="purchase_requests")
    number = models.CharField(max_length=50, unique=True)

    requester = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT,
        related_name="purchase_requests",
    )
    service = models.ForeignKey(
        "organizations.Service", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="purchase_requests",
    )
    department = models.CharField(max_length=100, blank=True)
    purpose = models.TextField(blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="BROUILLON")
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default="NORMALE")

    # Validation
    validated_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="validated_purchase_requests",
    )
    validated_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    # Commande
    ordered_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="ordered_purchase_requests",
    )
    ordered_at = models.DateTimeField(null=True, blank=True)
    supplier_name = models.CharField(max_length=200, blank=True)
    expected_delivery = models.DateField(null=True, blank=True)

    # Reception
    received_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="received_purchase_requests",
    )
    received_at = models.DateTimeField(null=True, blank=True)

    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency_code = models.CharField(max_length=3, default="XOF")

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status", "-created_at"]),
        ]
        verbose_name = "Demande d'achat"

    def __str__(self):
        return f"{self.number} - {self.requester.email}"

    @property
    def is_editable(self):
        return self.status == "BROUILLON"

    @property
    def is_pending(self):
        return self.status in ("SOUMISE",)

    @property
    def can_validate(self):
        return self.status == "SOUMISE"

    @property
    def item_count(self):
        return self.items.count()

    def compute_total(self):
        from decimal import Decimal
        total = sum((item.subtotal for item in self.items.all()), Decimal("0"))
        self.total_amount = total
        self.save(update_fields=["total_amount"])
        return total


# ═══════════════════════════════════════════════════════════════
# LIGNE DE DEMANDE
# ═══════════════════════════════════════════════════════════════
class PurchaseRequestItem(models.Model):
    """Ligne d'une demande d'achat."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request = models.ForeignKey(PurchaseRequest, on_delete=models.CASCADE, related_name="items")
    item = models.ForeignKey(DAItem, on_delete=models.PROTECT, related_name="request_lines")
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.CharField(max_length=255, blank=True)
    quantity_received = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["item__category__display_order", "item__name"]
        unique_together = [("request", "item")]

    def __str__(self):
        return f"{self.item.name} x{self.quantity}"

    @property
    def subtotal(self):
        from decimal import Decimal
        return Decimal(str(self.unit_price)) * self.quantity

    @property
    def is_fully_received(self):
        return self.quantity_received >= self.quantity


# ═══════════════════════════════════════════════════════════════
# HISTORIQUE WORKFLOW
# ═══════════════════════════════════════════════════════════════
class PurchaseRequestHistory(models.Model):
    """Historique des changements de statut."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request = models.ForeignKey(PurchaseRequest, on_delete=models.CASCADE, related_name="history")
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(max_length=20)
    actor = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Historiques DA"

    def __str__(self):
        return f"{self.request.number}: {self.from_status} -> {self.to_status}"


# ═══════════════════════════════════════════════════════════════
# MOUVEMENT DE STOCK INTERNE
# ═══════════════════════════════════════════════════════════════
class DAStockMovement(TenantModel):
    """Mouvement de stock d'un article interne."""
    TYPE_CHOICES = [
        ("IN", "Entree (reception DA)"),
        ("OUT", "Sortie (attribution)"),
        ("ADJUST", "Ajustement"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="da_stock_movements")
    item = models.ForeignKey(DAItem, on_delete=models.CASCADE, related_name="movements")
    movement_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    quantity = models.IntegerField()
    stock_before = models.PositiveIntegerField()
    stock_after = models.PositiveIntegerField()
    reason = models.CharField(max_length=200, blank=True)
    purchase_request = models.ForeignKey(
        PurchaseRequest, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="stock_movements",
    )
    actor = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Mouvement stock DA"

    def __str__(self):
        sign = "+" if self.quantity > 0 else ""
        return f"{self.item.name}: {sign}{self.quantity}"


# ═══════════════════════════════════════════════════════════════
# SIGNATURE NUMERIQUE
# ═══════════════════════════════════════════════════════════════
class DASignature(TenantModel):
    """Une signature numerique apposee sur une DA."""
    SIGNATURE_LEVELS = [
        ("SIMPLE", "Simple (mot de passe)"),
        ("PIN_OTP", "PIN + OTP SMS"),
        ("CERTIFICATE", "Certificat X.509"),
    ]
    SIGNER_ROLES = [
        ("SERVICE_CHIEF", "Chef de service (emission)"),
        ("DIRECTOR", "Directeur de direction (visa)"),
        ("ACHATS_DIRECTOR", "Directeur des Achats (verification)"),
        ("DG", "Directeur General (engagement)"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="da_signatures",
    )
    purchase_request = models.ForeignKey(
        PurchaseRequest, on_delete=models.CASCADE,
        null=True, blank=True, related_name="signatures",
    )

    signer = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="da_signatures",
    )
    signer_role = models.CharField(max_length=20, choices=SIGNER_ROLES)
    signature_level = models.CharField(max_length=15, choices=SIGNATURE_LEVELS, default="PIN_OTP")

    signature_hash = models.CharField(max_length=64, unique=True, db_index=True)
    document_hash = models.CharField(max_length=64)

    otp_verified = models.BooleanField(default=False)
    otp_verified_at = models.DateTimeField(null=True, blank=True)

    signed_at = models.DateTimeField(auto_now_add=True)
    signed_ip = models.GenericIPAddressField(null=True, blank=True)
    signed_user_agent = models.TextField(blank=True)

    visual_image = models.ImageField(
        upload_to="da/signatures/", null=True, blank=True,
    )
    qr_code_image = models.ImageField(
        upload_to="da/qrcodes/", null=True, blank=True,
    )

    comment = models.CharField(max_length=255, blank=True)
    is_revoked = models.BooleanField(default=False)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["signed_at"]
        indexes = [
            models.Index(fields=["organization", "signer", "-signed_at"]),
            models.Index(fields=["purchase_request", "signed_at"]),
        ]
        verbose_name = "Signature DA"

    def __str__(self):
        return f"{self.signer_role} - {self.signer.email} - {self.signed_at.strftime('%d/%m/%Y')}"

    @property
    def is_valid(self):
        return not self.is_revoked


# ═══════════════════════════════════════════════════════════════
# WORKFLOW SIGNATURE
# ═══════════════════════════════════════════════════════════════
class DASignatureFlow(models.Model):
    """Definit l'ordre des signatures requises pour une DA."""
    STATUS_CHOICES = [
        ("PENDING", "En attente"),
        ("SIGNED", "Signe"),
        ("REJECTED", "Refuse"),
        ("SKIPPED", "Ignore"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    purchase_request = models.ForeignKey(
        PurchaseRequest, on_delete=models.CASCADE, related_name="signature_flow",
    )
    step_order = models.PositiveIntegerField()
    role_required = models.CharField(max_length=20, choices=DASignature.SIGNER_ROLES)
    assigned_to = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="pending_signatures",
    )

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")
    signature = models.OneToOneField(
        DASignature, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="flow_step",
    )

    rejected_reason = models.TextField(blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    comment = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["purchase_request", "step_order"]
        constraints = [
            models.UniqueConstraint(
                fields=["purchase_request", "step_order"],
                name="unique_signature_step_per_request",
            ),
        ]
        verbose_name = "Etape de signature"

    def __str__(self):
        return f"{self.purchase_request.number} - Etape {self.step_order}"

    @property
    def is_pending(self):
        return self.status == "PENDING"


# ═══════════════════════════════════════════════════════════════
# OTP SIGNATURE
# ═══════════════════════════════════════════════════════════════
class DAOtpCode(models.Model):
    """Code OTP temporaire pour valider une signature."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="da_otp_codes",
    )
    signature_flow = models.ForeignKey(
        DASignatureFlow, on_delete=models.CASCADE, related_name="otp_codes",
    )

    code_hash = models.CharField(max_length=64)
    sent_to = models.CharField(max_length=20)
    attempts = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=3)

    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Code OTP DA"

    def __str__(self):
        return f"OTP {self.user.email} ({'utilise' if self.is_used else 'actif'})"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        return not self.is_used and not self.is_expired and self.attempts < self.max_attempts
