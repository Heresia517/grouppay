"""
Services métier catalogue.

Couvre :
- RG-01, RG-23 : décrément stock atomique (variant ou produit)
- RG-04 : restauration stock au refus
- RG-08 : limite d'achat par membre
- RG-21 : alerte stock critique
- RG-22 : interdit stock négatif
"""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F


class StockError(Exception):
    """Erreur métier générique sur le stock."""


class InsufficientStockError(StockError):
    pass


class MaxPerMemberExceededError(StockError):
    pass


@transaction.atomic
def decrement_stock(product, quantity):
    """
    RG-01 : verrou + décrément atomique. Lève si stock insuffisant.
    RG-22 : empêche le stock négatif (double sécurité avec CheckConstraint).
    """
    from .models import Product

    if quantity <= 0:
        raise ValidationError("La quantité doit être > 0.")

    locked = Product.objects.select_for_update().get(pk=product.pk)
    if locked.stock_quantity < quantity:
        raise InsufficientStockError(
            f"Stock insuffisant pour {locked.name} "
            f"(demandé: {quantity}, dispo: {locked.stock_quantity})"
        )

    stock_before = locked.stock_quantity
    locked.stock_quantity = F("stock_quantity") - quantity
    locked.save(update_fields=["stock_quantity"])
    locked.refresh_from_db(fields=["stock_quantity"])

    # Historique mouvement
    from .models import StockMovement, StockAlert
    StockMovement.objects.create(
        organization=locked.organization,
        product=locked,
        movement_type="OUT",
        quantity=-quantity,
        stock_before=stock_before,
        stock_after=locked.stock_quantity,
        reason="Sortie commande",
    )

    # Créer une alerte si franchissement du seuil
    if stock_before > locked.reorder_level >= locked.stock_quantity:
        StockAlert.objects.create(
            organization=locked.organization,
            product=locked,
            stock_at_alert=locked.stock_quantity,
            reorder_level=locked.reorder_level,
        )

    return True


@transaction.atomic
def increment_stock(product, quantity):
    """RG-04 : restaure le stock (annulation, refus, retour)."""
    from .models import Product

    if quantity <= 0:
        raise ValidationError("La quantité doit être > 0.")

    locked = Product.objects.select_for_update().get(pk=product.pk)
    stock_before = locked.stock_quantity
    locked.stock_quantity = F("stock_quantity") + quantity
    locked.save(update_fields=["stock_quantity"])
    locked.refresh_from_db(fields=["stock_quantity"])

    from .models import StockMovement, StockAlert
    StockMovement.objects.create(
        organization=locked.organization,
        product=locked,
        movement_type="RESTORE",
        quantity=quantity,
        stock_before=stock_before,
        stock_after=locked.stock_quantity,
        reason="Restauration stock",
    )

    # Résoudre les alertes actives si on remonte au-dessus du seuil
    if stock_before <= locked.reorder_level < locked.stock_quantity:
        from django.utils import timezone
        StockAlert.objects.filter(
            product=locked, is_resolved=False,
        ).update(is_resolved=True, resolved_at=timezone.now())

    return True


def check_low_stock(organization):
    """
    RG-21 : retourne les produits sous leur seuil de réappro.
    Utilisé par la tâche Celery quotidienne pour notifier les gestionnaires.
    """
    from .models import Product

    return list(
        Product.objects.filter(
            organization=organization,
            is_active=True,
            stock_quantity__lte=F("reorder_level"),
        ).values("id", "name", "stock_quantity", "reorder_level")
    )


def check_max_per_member(user, product, quantity):
    """
    RG-08 : bloque si la quantité dépasse Product.max_per_member
    pour l'utilisateur courant (cumul panier + déjà commandé).
    """
    if not product.max_per_member:
        return True  # pas de limite

    from apps.orders.models import OrderItem

    # Déjà commandé (non refusé/annulé)
    already_ordered = OrderItem.objects.filter(
        order__member=user,
        product=product,
        order__status__in=["EN_ATTENTE_VALIDATION", "VALIDEE", "EN_LIVRAISON", "LIVREE"],
    ).aggregate(total=F("quantity"))
    # Note : aggregate simple, à affiner si besoin multi-statuts

    deja = OrderItem.objects.filter(
        order__member=user,
        product=product,
        order__status__in=["EN_ATTENTE_VALIDATION", "VALIDEE", "EN_LIVRAISON", "LIVREE"],
    )
    total_deja = sum(i.quantity for i in deja)

    if total_deja + quantity > product.max_per_member:
        raise MaxPerMemberExceededError(
            f"Limite d'achat atteinte pour {product.name} "
            f"(max {product.max_per_member}, déjà {total_deja})."
        )
    return True
