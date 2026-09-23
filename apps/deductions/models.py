import uuid
from django.db import models
from apps.organizations.models import Organization


class DeductionExportBatch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="export_batches")
    period_start = models.DateField()
    period_end = models.DateField()
    file = models.FileField(upload_to="deduction_exports/", null=True, blank=True)
    row_count = models.PositiveIntegerField(default=0)
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
    export_batch = models.ForeignKey(DeductionExportBatch, on_delete=models.SET_NULL, null=True, blank=True, related_name="transmissions")
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
