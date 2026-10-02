import uuid
from django.db import models
from apps.orders.models import Order
from apps.accounts.models import User


class Delivery(models.Model):
    STATUS_CHOICES = [
        ("CREEE", "Créée"),
        ("AFFECTEE", "Affectée"),
        ("EN_ROUTE", "En route"),
        ("EN_COURS", "En cours"),         # legacy, gardé pour compat
        ("LIVREE", "Livrée"),
        ("RETOURNEE", "Retournée"),
        ("PERDUE", "Perdue"),
        ("ECHEC", "Échec"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="delivery")
    courier = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="deliveries")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="CREEE")

    tracking_number = models.CharField(max_length=50, blank=True)
    carrier_name = models.CharField(max_length=100, blank=True)
    estimated_delivery_date = models.DateField(null=True, blank=True)
    recipient_notes = models.TextField(blank=True)

    attempts = models.PositiveIntegerField(default=0)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.CharField(max_length=255, blank=True)

    signature_image = models.ImageField(upload_to="signatures/", null=True, blank=True)
    delivery_photo = models.ImageField(upload_to="deliveries/", null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Livraison {self.order.order_number} [{self.status}]"


class DeliveryNoteDocument(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    delivery = models.OneToOneField(Delivery, on_delete=models.CASCADE, related_name="document")
    file = models.FileField(upload_to="delivery_notes/")
    file_hash = models.CharField(max_length=64, blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)
