import uuid
from datetime import timedelta
from django.db import models
from django.utils import timezone
from apps.organizations.models import Organization


class DeductionExportBatch(models.Model):
    STATUS_CHOICES = [
        ("DRAFT", "Brouillon"),
        ("READY", "Prêt"),
        ("DOWNLOADED", "Téléchargé"),
        ("CONFIRMED", "Confirmé"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="export_batches")
    period_start = models.DateField()
    period_end = models.DateField()
    file = models.FileField(upload_to="deduction_exports/", null=True, blank=True)
    file_hash = models.CharField(max_length=64, blank=True)
    row_count = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="DRAFT")
    generated_by = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, null=True)
    downloaded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class DeductionTransmission(models.Model):
    STATUS_CHOICES = [
        ("EN_ATTENTE", "En attente"),
        ("ENVOYEE", "Envoyée"),
        ("CONFIRMEE", "Confirmée"),
        ("ECHEC", "Échec"),
        ("EXPIREE", "Expirée"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField("orders.Order", on_delete=models.CASCADE, related_name="deduction_transmission")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="deduction_transmissions")
    reference = models.CharField(max_length=40, unique=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="EN_ATTENTE")

    # Snapshot identité membre (utilisé dans l'export CSV)
    member_email = models.EmailField(blank=True)
    member_internal_id = models.CharField(max_length=50, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency_code = models.CharField(max_length=3, blank=True)

    export_batch = models.ForeignKey(DeductionExportBatch, on_delete=models.SET_NULL, null=True, blank=True, related_name="transmissions")

    transmission_count = models.PositiveIntegerField(default=0)
    last_transmission_at = models.DateTimeField(null=True, blank=True)
    confirmation_reference = models.CharField(max_length=255, blank=True)
    error_message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        # RG-11 : expiration auto à 30 jours si non définie
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=30)
        # Snapshot membre
        if self.order_id and not self.member_email:
            self.member_email = self.order.member.email
            self.member_internal_id = self.order.member.internal_id
            self.amount = self.order.total_amount
            self.currency_code = self.order.currency_code
        super().save(*args, **kwargs)
