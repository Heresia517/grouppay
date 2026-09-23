from django.db import models


class TenantManager(models.Manager):
    """Impose le filtre organization sur tout modèle métier — RG-05."""
    def for_organization(self, organization):
        return self.get_queryset().filter(organization=organization)


class TenantModel(models.Model):
    """Hérite de ça pour tout modèle métier lié à une organization
    (Product, Order, etc. — pas Organization elle-même)."""
    objects = TenantManager()

    class Meta:
        abstract = True
