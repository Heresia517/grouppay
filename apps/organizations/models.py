import uuid
from django.db import models


class Organization(models.Model):
    STATUS_CHOICES = [
        ("TRIAL", "Trial"),
        ("ACTIVE", "Active"),
        ("SUSPENDED", "Suspended"),
        ("ARCHIVED", "Archivée"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=150, unique=True)
    logo = models.ImageField(upload_to="logos/", null=True, blank=True)
    color_primary = models.CharField(max_length=7, default="#EF233C")
    color_secondary = models.CharField(max_length=7, default="#2A9D8F")
    country_code = models.CharField(max_length=2, default="BF")
    currency_code = models.CharField(max_length=3, default="XOF")
    timezone = models.CharField(max_length=50, default="UTC")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="TRIAL")

    website = models.URLField(blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    max_users = models.PositiveIntegerField(default=1000)
    storage_gb = models.PositiveIntegerField(default=10)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name
