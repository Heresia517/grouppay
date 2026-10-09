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

    # Modules actifs (JSON array) : ["mutuelle", "da"]
    modules_enabled = models.JSONField(
        default=list,
        blank=True,
        help_text="Modules actifs : mutuelle, da",
    )

    website = models.URLField(blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    max_users = models.PositiveIntegerField(default=1000)
    storage_gb = models.PositiveIntegerField(default=10)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    def has_module(self, module_name):
        """Verifie si un module est active pour cette organisation."""
        return module_name in (self.modules_enabled or [])

    def __str__(self):
        return self.name



class Direction(models.Model):
    """Direction d'une organisation (ex: Direction Technique, Direction Achats)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="directions",
    )
    code = models.CharField(max_length=20, help_text="Code court (ex: DT, DA, DAF)")
    name = models.CharField(max_length=150, help_text="Nom complet")
    description = models.TextField(blank=True)
    director = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="directed_directions",
        help_text="Directeur de cette direction",
    )
    is_achats = models.BooleanField(
        default=False,
        help_text="Marquer comme Direction des Achats",
    )
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["display_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"],
                name="unique_direction_code_per_org",
            ),
        ]
        verbose_name = "Direction"

    def __str__(self):
        return f"{self.code} - {self.name}"


class Service(models.Model):
    """Service rattache a une Direction (ex: Service Maintenance)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="services",
    )
    direction = models.ForeignKey(
        Direction, on_delete=models.CASCADE, related_name="services",
    )
    code = models.CharField(max_length=20, help_text="Code court (ex: MAINT)")
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    chief = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="led_services",
        help_text="Chef de ce service",
    )
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["direction__display_order", "display_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"],
                name="unique_service_code_per_org",
            ),
        ]
        verbose_name = "Service"

    def __str__(self):
        return f"{self.code} - {self.name}"
