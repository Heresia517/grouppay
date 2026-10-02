import uuid
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.db.models import Q
from apps.organizations.models import Organization


class UserManager(BaseUserManager):
    def create_user(self, email, organization, password=None, **extra_fields):
        if not email:
            raise ValueError("L'email est obligatoire")
        email = self.normalize_email(email)
        if not isinstance(organization, Organization):
            organization = Organization.objects.get(pk=organization)
        user = self.model(email=email, organization=organization, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, organization, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "ADMIN")
        return self.create_user(email, organization, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ("ADMIN", "Admin"),
        ("GESTIONNAIRE", "Gestionnaire"),
        ("FOURNISSEUR", "Fournisseur"),
        ("LIVREUR", "Livreur"),
        ("MEMBRE", "Membre"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="users")
    email = models.EmailField()
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    internal_id = models.CharField(max_length=50, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="MEMBRE")
    is_active = models.BooleanField(default=True)
    is_blocked = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    failed_login_count = models.PositiveIntegerField(default=0)
    theme_preference = models.CharField(
        max_length=10,
        choices=[("light", "Clair"), ("dark", "Sombre")],
        default="light",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["organization"]

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization", "email"], name="unique_email_per_org"),
            models.UniqueConstraint(fields=["organization", "internal_id"], name="unique_internal_id_per_org", condition=~Q(internal_id="")),
        ]

    def __str__(self):
        return f"{self.email} ({self.organization.name})"
