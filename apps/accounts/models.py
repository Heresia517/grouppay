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
    phone = models.CharField(max_length=20, blank=True)

    # Rattachement organisationnel
    service = models.ForeignKey(
        "organizations.Service", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="members",
        help_text="Service auquel appartient l'utilisateur",
    )
    is_service_chief = models.BooleanField(
        default=False,
        help_text="Chef de service (peut soumettre des DA)",
    )
    is_director = models.BooleanField(
        default=False,
        help_text="Directeur de direction (peut viser les DA)",
    )
    is_dg = models.BooleanField(
        default=False,
        help_text="Directeur General (signature finale des DA)",
    )

    referred_by = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="referred_users",
    )
    referral_reward_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
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



class Referral(models.Model):
    """Parrainage entre membres."""
    STATUS_CHOICES = [
        ("PENDING", "En attente"),
        ("ACTIVE", "Actif"),
        ("REWARDED", "Recompense"),
        ("EXPIRED", "Expire"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="referrals",
    )
    referrer = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="referrals_made",
    )
    referred = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="referrals_received",
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")
    reward_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    rewarded_at = models.DateTimeField(null=True, blank=True)
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["referrer", "referred"], name="unique_referral_pair"),
        ]
        verbose_name = "Parrainage"

    def __str__(self):
        return f"{self.referrer.email} -> {self.referred.email}"


class ReferralCode(models.Model):
    """Code de parrainage personnel."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField("accounts.User", on_delete=models.CASCADE, related_name="referral_code")
    code = models.CharField(max_length=20, unique=True, db_index=True)
    uses_count = models.PositiveIntegerField(default=0)
    max_uses = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.code

    @property
    def can_be_used(self):
        if not self.is_active:
            return False
        if self.max_uses is not None and self.uses_count >= self.max_uses:
            return False
        return True
