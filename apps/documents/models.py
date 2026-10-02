import uuid
from django.db import models
from apps.orders.models import Order


class PurchaseOrderDocument(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="purchase_order_document")
    file = models.FileField(upload_to="purchase_orders/")
    generated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"BC_{self.order.order_number}"



class InvoiceDocument(models.Model):
    """Facture PDF liée à une commande."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(
        "orders.Order", on_delete=models.CASCADE, related_name="invoice_document",
    )
    invoice_number = models.CharField(max_length=50, unique=True)
    file = models.FileField(upload_to="invoices/", null=True, blank=True)
    file_hash = models.CharField(max_length=64, blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    downloaded_at = models.DateTimeField(null=True, blank=True)
    download_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Facture {self.invoice_number}"
