"""Services du module Inventaire."""
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum, Count
from django.utils import timezone


def generate_asset_reference(organization, category):
    """Genere une reference unique : INV-<CAT>-000001."""
    from .models import Asset

    prefix = f"INV-{category.code}-"
    count = Asset.objects.filter(
        organization=organization, reference__startswith=prefix,
    ).count()
    return f"{prefix}{count + 1:06d}"


@transaction.atomic
def assign_asset(asset, user, assigned_by=None, notes=""):
    """Attribue un actif a un utilisateur."""
    from .models import AssetAssignment, AssetMovement

    if asset.status not in ("AVAILABLE", "ASSIGNED"):
        raise ValueError(f"Impossible d'attribuer un actif en {asset.get_status_display()}")

    # Si deja attribue, retour d'abord
    if asset.status == "ASSIGNED":
        return_asset(asset, returned_by=assigned_by, notes="Reattribution")

    old_status = asset.status
    old_location = asset.location

    asset.assigned_to = user
    asset.assigned_at = timezone.now()
    asset.status = "ASSIGNED"
    asset.save()

    AssetAssignment.objects.create(
        asset=asset,
        assigned_to=user,
        assigned_by=assigned_by,
        condition_at_assignment=asset.condition,
        notes=notes,
    )

    AssetMovement.objects.create(
        asset=asset,
        from_status=old_status,
        to_status="ASSIGNED",
        from_location=old_location,
        to_location=f"Attribue a {user.email}",
        actor=assigned_by,
        reason="Attribution",
    )

    return asset


@transaction.atomic
def return_asset(asset, returned_by=None, notes=""):
    """Retourne un actif."""
    from .models import AssetAssignment, AssetMovement

    if asset.status != "ASSIGNED":
        raise ValueError("Cet actif n'est pas attribue")

    # Mettre a jour la derniere attribution
    assignment = asset.assignments.filter(returned_at__isnull=True).first()
    if assignment:
        assignment.returned_at = timezone.now()
        assignment.condition_at_return = asset.condition
        if notes:
            assignment.notes = f"{assignment.notes}\n{notes}".strip()
        assignment.save()

    old_status = asset.status
    user_email = asset.assigned_to.email if asset.assigned_to else ""

    asset.assigned_to = None
    asset.assigned_at = None
    asset.status = "AVAILABLE"
    asset.save()

    AssetMovement.objects.create(
        asset=asset,
        from_status=old_status,
        to_status="AVAILABLE",
        from_location=f"Attribue a {user_email}",
        to_location="Retour",
        actor=returned_by,
        reason="Retour",
    )

    return asset


@transaction.atomic
def record_maintenance(asset, maintenance_type, description, cost=0,
                       performed_by="", next_date=None, actor=None):
    """Enregistre une maintenance."""
    from .models import MaintenanceRecord, AssetMovement

    record = MaintenanceRecord.objects.create(
        asset=asset,
        type=maintenance_type,
        date=date.today(),
        performed_by=performed_by,
        cost=Decimal(str(cost)),
        description=description,
        next_maintenance_date=next_date,
        performed_by_user=actor,
    )

    old_status = asset.status
    asset.last_maintenance = date.today()
    if next_date:
        asset.next_maintenance = next_date
    else:
        months = asset.maintenance_interval_months or 12
        asset.next_maintenance = date.today() + timedelta(days=30 * months)

    # Remettre en disponibilite apres maintenance
    if asset.status == "MAINTENANCE":
        asset.status = "AVAILABLE"

    asset.save()

    AssetMovement.objects.create(
        asset=asset,
        from_status=old_status,
        to_status=asset.status,
        actor=actor,
        reason=f"Maintenance {maintenance_type}",
    )

    return record


def get_inventory_stats(organization):
    """Statistiques globales de l'inventaire."""
    from .models import Asset

    qs = Asset.objects.filter(organization=organization, is_active=True)

    by_status = dict(
        qs.values_list("status").annotate(c=Count("id")).values_list("status", "c")
    )
    by_condition = dict(
        qs.values_list("condition").annotate(c=Count("id")).values_list("condition", "c")
    )

    # Valeur totale
    total_value = sum(a.computed_value for a in qs if a.computed_value)

    # Actifs necessitant maintenance
    today = date.today()
    needs_maintenance = qs.filter(
        next_maintenance__lte=today,
    ).exclude(status__in=["RETIRED", "LOST", "STOLEN"]).count()

    return {
        "total": qs.count(),
        "available": by_status.get("AVAILABLE", 0),
        "assigned": by_status.get("ASSIGNED", 0),
        "maintenance": by_status.get("MAINTENANCE", 0),
        "retired": by_status.get("RETIRED", 0) + by_status.get("LOST", 0) + by_status.get("STOLEN", 0),
        "total_value": total_value,
        "needs_maintenance": needs_maintenance,
        "by_condition": by_condition,
    }


def get_category_stats(organization):
    """Stats par categorie."""
    from .models import AssetCategory, Asset

    categories = AssetCategory.objects.filter(organization=organization, is_active=True)
    result = []

    for cat in categories:
        assets = Asset.objects.filter(category=cat, is_active=True)
        total_val = sum(a.computed_value for a in assets if a.computed_value)
        result.append({
            "category": cat,
            "count": assets.count(),
            "total_value": total_val,
        })

    return result
