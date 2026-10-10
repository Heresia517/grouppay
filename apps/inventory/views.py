"""Vues du module Inventaire."""
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q, Count, Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import (
    AssetCategory, Asset, AssetAssignment, MaintenanceRecord, AssetMovement,
)
from .services import (
    generate_asset_reference, assign_asset, return_asset,
    record_maintenance, get_inventory_stats, get_category_stats,
)


def _require_manager(user):
    if user.role not in ("ADMIN", "GESTIONNAIRE") and not user.is_dg:
        raise PermissionDenied("Reserve aux gestionnaires")


def _can_view(user):
    """Tout user authentifie peut voir l'inventaire."""
    return user.is_authenticated


# ═══════════════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════════════
@login_required
def inventory_dashboard(request):
    """Dashboard inventaire."""
    org = request.user.organization

    stats = get_inventory_stats(org)
    categories_data = get_category_stats(org)

    # Assets recents
    recent_assets = Asset.objects.filter(
        organization=org, is_active=True,
    ).select_related("category", "assigned_to").order_by("-created_at")[:10]

    # Maintenance urgente
    today = date.today()
    maintenance_urgent = Asset.objects.filter(
        organization=org, is_active=True,
        next_maintenance__lte=today + timedelta(days=30),
    ).exclude(status__in=["RETIRED", "LOST", "STOLEN"]).order_by("next_maintenance")[:10]

    return render(request, "inventory/dashboard.html", {
        "stats": stats,
        "categories_data": categories_data,
        "recent_assets": recent_assets,
        "maintenance_urgent": maintenance_urgent,
    })


# ═══════════════════════════════════════════════════════════════
# LISTE ASSETS
# ═══════════════════════════════════════════════════════════════
@login_required
def asset_list(request):
    """Liste des actifs avec filtres."""
    org = request.user.organization

    q = (request.GET.get("q") or "").strip()
    category_id = request.GET.get("category", "")
    status_filter = request.GET.get("status", "")
    condition_filter = request.GET.get("condition", "")

    assets = Asset.objects.filter(organization=org, is_active=True).select_related(
        "category", "assigned_to",
    )

    if q:
        assets = assets.filter(
            Q(name__icontains=q) | Q(reference__icontains=q) |
            Q(serial_number__icontains=q) | Q(brand__icontains=q)
        )
    if category_id:
        assets = assets.filter(category_id=category_id)
    if status_filter:
        assets = assets.filter(status=status_filter)
    if condition_filter:
        assets = assets.filter(condition=condition_filter)

    assets = assets.order_by("-created_at")
    categories = AssetCategory.objects.filter(organization=org, is_active=True)

    return render(request, "inventory/asset_list.html", {
        "assets": assets,
        "categories": categories,
        "statuses": Asset.STATUS_CHOICES,
        "conditions": Asset.CONDITION_CHOICES,
        "filters": {
            "q": q, "category": category_id,
            "status": status_filter, "condition": condition_filter,
        },
    })


# ═══════════════════════════════════════════════════════════════
# DETAIL ASSET
# ═══════════════════════════════════════════════════════════════
@login_required
def asset_detail(request, asset_id):
    """Detail d'un actif."""
    asset = get_object_or_404(
        Asset.objects.select_related("category", "assigned_to"),
        id=asset_id,
        organization=request.user.organization,
    )

    assignments = asset.assignments.select_related("assigned_to", "assigned_by").order_by("-assigned_at")
    maintenances = asset.maintenance_records.order_by("-date")
    movements = asset.movements.select_related("actor").order_by("-created_at")

    return render(request, "inventory/asset_detail.html", {
        "asset": asset,
        "assignments": assignments,
        "maintenances": maintenances,
        "movements": movements,
    })


# ═══════════════════════════════════════════════════════════════
# CRUD ASSET
# ═══════════════════════════════════════════════════════════════
@login_required
def asset_form(request, asset_id=None):
    """Creer / modifier un actif."""
    _require_manager(request.user)
    org = request.user.organization

    asset = None
    if asset_id:
        asset = get_object_or_404(Asset, id=asset_id, organization=org)

    categories = AssetCategory.objects.filter(organization=org, is_active=True)

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        category_id = request.POST.get("category")
        serial_number = (request.POST.get("serial_number") or "").strip()
        brand = (request.POST.get("brand") or "").strip()
        model_name = (request.POST.get("model_name") or "").strip()
        description = (request.POST.get("description") or "").strip()
        location = (request.POST.get("location") or "").strip()
        status = request.POST.get("status", "AVAILABLE")
        condition = request.POST.get("condition", "NEW")
        notes = (request.POST.get("notes") or "").strip()

        errors = []
        if not name:
            errors.append("Le nom est obligatoire.")
        if not category_id:
            errors.append("La categorie est obligatoire.")

        try:
            purchase_price = Decimal(request.POST.get("purchase_price") or "0")
        except (InvalidOperation, ValueError):
            purchase_price = Decimal("0")

        try:
            depreciation_rate = Decimal(request.POST.get("depreciation_rate") or "20")
        except (InvalidOperation, ValueError):
            depreciation_rate = Decimal("20")

        purchase_date_str = request.POST.get("purchase_date")
        warranty_end_str = request.POST.get("warranty_end_date")

        purchase_date = None
        if purchase_date_str:
            try:
                from datetime import datetime
                purchase_date = datetime.strptime(purchase_date_str, "%Y-%m-%d").date()
            except ValueError:
                pass

        warranty_end_date = None
        if warranty_end_str:
            try:
                from datetime import datetime
                warranty_end_date = datetime.strptime(warranty_end_str, "%Y-%m-%d").date()
            except ValueError:
                pass

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, "inventory/asset_form.html", {
                "asset": asset, "categories": categories,
                "statuses": Asset.STATUS_CHOICES,
                "conditions": Asset.CONDITION_CHOICES,
            })

        category = get_object_or_404(AssetCategory, id=category_id, organization=org)

        if asset:
            asset.name = name
            asset.category = category
            asset.serial_number = serial_number
            asset.brand = brand
            asset.model_name = model_name
            asset.description = description
            asset.location = location
            asset.status = status
            asset.condition = condition
            asset.notes = notes
            asset.purchase_price = purchase_price if purchase_price else None
            asset.purchase_date = purchase_date
            asset.warranty_end_date = warranty_end_date
            asset.depreciation_rate = depreciation_rate
            asset.save()
            messages.success(request, f"Actif « {name} » mis a jour.")
        else:
            asset = Asset.objects.create(
                organization=org,
                category=category,
                reference=generate_asset_reference(org, category),
                name=name,
                serial_number=serial_number,
                brand=brand,
                model_name=model_name,
                description=description,
                location=location,
                status=status,
                condition=condition,
                notes=notes,
                purchase_price=purchase_price if purchase_price else None,
                purchase_date=purchase_date,
                warranty_end_date=warranty_end_date,
                depreciation_rate=depreciation_rate,
            )
            AssetMovement.objects.create(
                asset=asset,
                to_status=status,
                to_location=location,
                actor=request.user,
                reason="Creation",
            )
            messages.success(request, f"Actif « {name} » cree ({asset.reference}).")

        return redirect("asset_detail", asset_id=asset.id)

    return render(request, "inventory/asset_form.html", {
        "asset": asset, "categories": categories,
        "statuses": Asset.STATUS_CHOICES,
        "conditions": Asset.CONDITION_CHOICES,
    })


# ═══════════════════════════════════════════════════════════════
# ATTRIBUTION
# ═══════════════════════════════════════════════════════════════
@login_required
@require_POST
def asset_assign(request, asset_id):
    """Attribue un actif a un user."""
    _require_manager(request.user)
    asset = get_object_or_404(Asset, id=asset_id, organization=request.user.organization)

    from apps.accounts.models import User
    user_id = request.POST.get("user_id")
    notes = request.POST.get("notes", "").strip()

    user = get_object_or_404(User, id=user_id, organization=request.user.organization)

    try:
        assign_asset(asset, user, assigned_by=request.user, notes=notes)
        messages.success(request, f"Actif attribue a {user.email}")
    except ValueError as e:
        messages.error(request, str(e))

    return redirect("asset_detail", asset_id=asset.id)


@login_required
@require_POST
def asset_return(request, asset_id):
    """Retourne un actif."""
    _require_manager(request.user)
    asset = get_object_or_404(Asset, id=asset_id, organization=request.user.organization)
    notes = request.POST.get("notes", "").strip()

    try:
        return_asset(asset, returned_by=request.user, notes=notes)
        messages.success(request, "Actif retourne")
    except ValueError as e:
        messages.error(request, str(e))

    return redirect("asset_detail", asset_id=asset.id)


# ═══════════════════════════════════════════════════════════════
# MAINTENANCE
# ═══════════════════════════════════════════════════════════════
@login_required
def maintenance_form(request, asset_id):
    """Formulaire de maintenance."""
    _require_manager(request.user)
    asset = get_object_or_404(Asset, id=asset_id, organization=request.user.organization)

    if request.method == "POST":
        maintenance_type = request.POST.get("type", "PREVENTIVE")
        description = (request.POST.get("description") or "").strip()
        performed_by = (request.POST.get("performed_by") or "").strip()

        try:
            cost = Decimal(request.POST.get("cost") or "0")
        except (InvalidOperation, ValueError):
            cost = Decimal("0")

        next_date_str = request.POST.get("next_maintenance_date")
        next_date = None
        if next_date_str:
            try:
                from datetime import datetime
                next_date = datetime.strptime(next_date_str, "%Y-%m-%d").date()
            except ValueError:
                pass

        record_maintenance(
            asset, maintenance_type, description,
            cost=cost, performed_by=performed_by,
            next_date=next_date, actor=request.user,
        )

        messages.success(request, "Maintenance enregistree")
        return redirect("asset_detail", asset_id=asset.id)

    return render(request, "inventory/maintenance_form.html", {
        "asset": asset,
        "types": MaintenanceRecord.TYPE_CHOICES,
    })


@login_required
@require_POST
def asset_change_status(request, asset_id):
    """Change le statut d'un actif."""
    _require_manager(request.user)
    asset = get_object_or_404(Asset, id=asset_id, organization=request.user.organization)

    new_status = request.POST.get("status")
    reason = request.POST.get("reason", "").strip()

    valid_statuses = [c[0] for c in Asset.STATUS_CHOICES]
    if new_status not in valid_statuses:
        messages.error(request, "Statut invalide")
        return redirect("asset_detail", asset_id=asset.id)

    old_status = asset.status
    asset.status = new_status
    if new_status == "ASSIGNED":
        asset.assigned_to = None
        asset.assigned_at = None
    asset.save()

    AssetMovement.objects.create(
        asset=asset,
        from_status=old_status,
        to_status=new_status,
        actor=request.user,
        reason=reason or "Changement de statut",
    )

    messages.success(request, f"Statut change : {asset.get_status_display()}")
    return redirect("asset_detail", asset_id=asset.id)
