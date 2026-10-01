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
