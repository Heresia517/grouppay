"""Vues Admin UI du module DA : CRUD articles + categories + directions."""
import csv
import io
import secrets
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.db.models import Q, Count
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import DACategory, DAItem, DAStockMovement
from apps.organizations.models import Direction, Service


# ═══════════════════════════════════════════════════════════════
# PERMISSIONS
# ═══════════════════════════════════════════════════════════════
def _require_admin_da(user):
    """Reserve aux ADMIN, DG, ou membres de la Direction des Achats."""
    if user.role == "ADMIN" or user.is_dg:
        return True
    if user.service and user.service.direction.is_achats:
        return True
    # Directeurs de la direction des achats
    if user.is_director and user.directed_directions.filter(is_achats=True).exists():
        return True
    raise PermissionDenied("Reserve aux administrateurs DA")


# ═══════════════════════════════════════════════════════════════
# HUB ADMIN
# ═══════════════════════════════════════════════════════════════
@login_required
def admin_home(request):
    """Hub Admin DA."""
    _require_admin_da(request.user)
    org = request.user.organization

    # Stats rapides
    stats = {
        "categories": DACategory.objects.filter(organization=org).count(),
        "items": DAItem.objects.filter(organization=org).count(),
        "items_low_stock": DAItem.objects.filter(
            organization=org, is_active=True, stock_quantity__lte=5,
        ).count(),
        "directions": Direction.objects.filter(organization=org).count(),
        "services": Service.objects.filter(organization=org).count(),
    }

    return render(request, "da/admin/home.html", {"stats": stats})


# ═══════════════════════════════════════════════════════════════
# CRUD CATEGORIES
# ═══════════════════════════════════════════════════════════════
@login_required
def admin_categories(request):
    """Liste des categories."""
    _require_admin_da(request.user)
    org = request.user.organization

    categories = DACategory.objects.filter(organization=org).annotate(
        item_count=Count("items"),
    ).order_by("display_order", "name")

    return render(request, "da/admin/categories.html", {"categories": categories})


@login_required
def admin_category_form(request, category_id=None):
    """Creer / modifier une categorie."""
    _require_admin_da(request.user)
    org = request.user.organization

    category = None
    if category_id:
        category = get_object_or_404(DACategory, id=category_id, organization=org)

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        description = (request.POST.get("description") or "").strip()
        icon = (request.POST.get("icon") or "").strip()
        display_order = request.POST.get("display_order") or 0
        is_active = request.POST.get("is_active") == "on"

        if not name:
            messages.error(request, "Le nom est obligatoire.")
            return render(request, "da/admin/category_form.html", {"category": category})

        try:
            display_order = int(display_order)
        except ValueError:
            display_order = 0

        if category:
            category.name = name
            category.description = description
            category.icon = icon
            category.display_order = display_order
            category.is_active = is_active
            category.save()
            messages.success(request, f"Categorie « {name} » mise a jour.")
        else:
            DACategory.objects.create(
                organization=org,
                name=name,
                description=description,
                icon=icon,
                display_order=display_order,
                is_active=is_active,
            )
            messages.success(request, f"Categorie « {name} » creee.")

        return redirect("da_admin_categories")

    return render(request, "da/admin/category_form.html", {"category": category})


@login_required
@require_POST
def admin_category_delete(request, category_id):
    """Supprimer une categorie (si vide)."""
    _require_admin_da(request.user)
    category = get_object_or_404(
        DACategory, id=category_id, organization=request.user.organization,
    )

    if category.items.exists():
        messages.error(request, f"Impossible : la categorie contient {category.items.count()} article(s).")
        return redirect("da_admin_categories")

    name = category.name
    category.delete()
    messages.success(request, f"Categorie « {name} » supprimee.")
    return redirect("da_admin_categories")


# ═══════════════════════════════════════════════════════════════
# CRUD ARTICLES
# ═══════════════════════════════════════════════════════════════
@login_required
def admin_items(request):
    """Liste des articles avec filtres + recherche."""
    _require_admin_da(request.user)
    org = request.user.organization

    q = (request.GET.get("q") or "").strip()
    category_id = request.GET.get("category", "")
    stock_filter = request.GET.get("stock", "")

    items = DAItem.objects.filter(organization=org).select_related("category")

    if q:
        items = items.filter(Q(name__icontains=q) | Q(reference__icontains=q))
    if category_id:
        items = items.filter(category_id=category_id)
    if stock_filter == "low":
        items = items.filter(stock_quantity__lte=5, is_active=True)
    elif stock_filter == "out":
        items = items.filter(stock_quantity=0)

    items = items.order_by("category__display_order", "name")

    categories = DACategory.objects.filter(organization=org, is_active=True)

    return render(request, "da/admin/items.html", {
        "items": items,
        "categories": categories,
        "filters": {"q": q, "category": category_id, "stock": stock_filter},
    })


@login_required
def admin_item_form(request, item_id=None):
    """Creer / modifier un article."""
    _require_admin_da(request.user)
    org = request.user.organization

    item = None
    if item_id:
        item = get_object_or_404(DAItem, id=item_id, organization=org)

    categories = DACategory.objects.filter(organization=org, is_active=True)

    if request.method == "POST":
        reference = (request.POST.get("reference") or "").strip()
        name = (request.POST.get("name") or "").strip()
        category_id = request.POST.get("category")
        unit = request.POST.get("unit", "PCS")
        description = (request.POST.get("description") or "").strip()

        try:
            unit_price = Decimal(request.POST.get("unit_price") or "0")
        except (InvalidOperation, ValueError):
            unit_price = Decimal("0")

        try:
            stock_quantity = int(request.POST.get("stock_quantity") or "0")
        except ValueError:
            stock_quantity = 0

        try:
            reorder_level = int(request.POST.get("reorder_level") or "5")
        except ValueError:
            reorder_level = 5

        max_per_request_raw = request.POST.get("max_per_request") or ""
        try:
            max_per_request = int(max_per_request_raw) if max_per_request_raw else None
        except ValueError:
            max_per_request = None

        is_active = request.POST.get("is_active") == "on"
        is_available_to_all = request.POST.get("is_available_to_all") == "on"

        errors = []
        if not name:
            errors.append("Le nom est obligatoire.")
        if not category_id:
            errors.append("La categorie est obligatoire.")

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, "da/admin/item_form.html", {
                "item": item, "categories": categories,
            })

        category = get_object_or_404(DACategory, id=category_id, organization=org)

        if item:
            item.reference = reference
            item.name = name
            item.category = category
            item.unit = unit
            item.description = description
            item.unit_price = unit_price
            item.stock_quantity = stock_quantity
            item.reorder_level = reorder_level
            item.max_per_request = max_per_request
            item.is_active = is_active
            item.is_available_to_all = is_available_to_all
            item.save()
            messages.success(request, f"Article « {name} » mis a jour.")
        else:
            DAItem.objects.create(
                organization=org,
                reference=reference,
                name=name,
                category=category,
                unit=unit,
                description=description,
                unit_price=unit_price,
                stock_quantity=stock_quantity,
                reorder_level=reorder_level,
                max_per_request=max_per_request,
                is_active=is_active,
                is_available_to_all=is_available_to_all,
            )
            messages.success(request, f"Article « {name} » cree.")

        return redirect("da_admin_items")

    return render(request, "da/admin/item_form.html", {
        "item": item, "categories": categories,
    })


@login_required
@require_POST
def admin_item_delete(request, item_id):
    """Desactive un article."""
    _require_admin_da(request.user)
    item = get_object_or_404(
        DAItem, id=item_id, organization=request.user.organization,
    )
    item.is_active = False
    item.save(update_fields=["is_active"])
    messages.success(request, f"Article « {item.name} » desactive.")
    return redirect("da_admin_items")


@login_required
@require_POST
def admin_item_toggle(request, item_id):
    """Active/desactive un article."""
    _require_admin_da(request.user)
    item = get_object_or_404(
        DAItem, id=item_id, organization=request.user.organization,
    )
    item.is_active = not item.is_active
    item.save(update_fields=["is_active"])
    messages.success(request, f"Article {'active' if item.is_active else 'desactive'}.")
    return redirect("da_admin_items")


# ═══════════════════════════════════════════════════════════════
# AJUSTEMENT DE STOCK
# ═══════════════════════════════════════════════════════════════
@login_required
@require_POST
def admin_item_stock_adjust(request, item_id):
    """Ajustement manuel du stock."""
    _require_admin_da(request.user)
    item = get_object_or_404(
        DAItem, id=item_id, organization=request.user.organization,
    )

    try:
        new_qty = int(request.POST.get("new_quantity", 0))
    except (ValueError, TypeError):
        messages.error(request, "Quantite invalide.")
        return redirect("da_admin_items")

    if new_qty < 0:
        messages.error(request, "La quantite ne peut pas etre negative.")
        return redirect("da_admin_items")

    reason = (request.POST.get("reason") or "").strip() or "Ajustement manuel"

    with transaction.atomic():
        stock_before = item.stock_quantity
        delta = new_qty - stock_before

        if delta != 0:
            item.stock_quantity = new_qty
            item.save(update_fields=["stock_quantity"])

            DAStockMovement.objects.create(
                organization=item.organization,
                item=item,
                movement_type="ADJUST",
                quantity=delta,
                stock_before=stock_before,
                stock_after=new_qty,
                reason=reason,
                actor=request.user,
            )

    messages.success(request, f"Stock ajuste : {stock_before} -> {new_qty}")
    return redirect("da_admin_items")


# ═══════════════════════════════════════════════════════════════
# IMPORT CSV ARTICLES
# ═══════════════════════════════════════════════════════════════
@login_required
def admin_items_import(request):
    """Page d'import CSV articles."""
    _require_admin_da(request.user)
    return render(request, "da/admin/items_import.html")


@login_required
@require_POST
def admin_items_import_upload(request):
    """Traite le fichier CSV uploade."""
    _require_admin_da(request.user)
    org = request.user.organization

    if "csv_file" not in request.FILES:
        messages.error(request, "Aucun fichier selectionne.")
        return redirect("da_admin_items_import")

    f = request.FILES["csv_file"]
    if not f.name.lower().endswith(".csv"):
        messages.error(request, "Le fichier doit etre un .csv")
        return redirect("da_admin_items_import")

    try:
        content = f.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        messages.error(request, "Encodage invalide. Utilisez UTF-8.")
        return redirect("da_admin_items_import")

    reader = csv.DictReader(io.StringIO(content))
    fieldnames = set(reader.fieldnames or [])
    required = {"name", "category"}
    if not required.issubset(fieldnames):
        messages.error(request, f"Colonnes requises : name, category. Trouvees : {fieldnames}")
        return redirect("da_admin_items_import")

    created = 0
    updated = 0
    errors = []

    for i, row in enumerate(reader, start=2):
        name = (row.get("name") or "").strip()
        category_name = (row.get("category") or "").strip()

        if not name or not category_name:
            errors.append(f"Ligne {i} : name ou category vide")
            continue

        category, _ = DACategory.objects.get_or_create(
            organization=org, name=category_name,
            defaults={"is_active": True},
        )

        reference = (row.get("reference") or "").strip()
        unit = (row.get("unit") or "PCS").strip().upper()
        if unit not in dict(DAItem.UNIT_CHOICES):
            unit = "PCS"

        try:
            unit_price = Decimal(row.get("unit_price") or "0")
        except (InvalidOperation, ValueError):
            unit_price = Decimal("0")

        try:
            stock_quantity = int(row.get("stock_quantity") or "0")
        except ValueError:
            stock_quantity = 0

        try:
            reorder_level = int(row.get("reorder_level") or "5")
        except ValueError:
            reorder_level = 5

        # Chercher par reference OU name
        existing = None
        if reference:
            existing = DAItem.objects.filter(organization=org, reference=reference).first()
        if not existing:
            existing = DAItem.objects.filter(organization=org, name=name).first()

        try:
            if existing:
                existing.name = name
                existing.category = category
                existing.unit = unit
                existing.unit_price = unit_price
                if not existing.stock_quantity:  # Ne pas ecraser si stock existant
                    existing.stock_quantity = stock_quantity
                existing.reorder_level = reorder_level
                existing.save()
                updated += 1
            else:
                DAItem.objects.create(
                    organization=org,
                    reference=reference,
                    name=name,
                    category=category,
                    unit=unit,
                    unit_price=unit_price,
                    stock_quantity=stock_quantity,
                    reorder_level=reorder_level,
                )
                created += 1
        except Exception as e:
            errors.append(f"Ligne {i} ({name}) : {e}")

    messages.success(
        request,
        f"Import termine : {created} crees, {updated} mis a jour."
    )
    if errors:
        messages.warning(request, f"{len(errors)} erreur(s) : " + " | ".join(errors[:5]))

    return redirect("da_admin_items")


@login_required
def admin_items_import_template(request):
    """Telecharge le modele CSV."""
    _require_admin_da(request.user)

    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = 'attachment; filename="modele-articles-da.csv"'
    resp.write("reference,name,category,unit,unit_price,stock_quantity,reorder_level\n")
    resp.write("PAP-A4-500,Papier A4 80g,Papeterie,REAM,3500,50,10\n")
    resp.write("STY-BIC-B,Stylos bille bleus,Papeterie,PCS,150,200,50\n")
    resp.write("CAR-HP-26A,Cartouche HP 26A,Consommables,PCS,45000,5,3\n")
    return resp


# ═══════════════════════════════════════════════════════════════
# GESTION DIRECTIONS + SERVICES
# ═══════════════════════════════════════════════════════════════
@login_required
def admin_directions(request):
    """Liste des directions."""
    _require_admin_da(request.user)
    org = request.user.organization

    directions = Direction.objects.filter(organization=org).annotate(
        service_count=Count("services"),
    ).order_by("display_order", "name")

    return render(request, "da/admin/directions.html", {"directions": directions})


@login_required
def admin_direction_form(request, direction_id=None):
    """Creer / modifier une direction."""
    _require_admin_da(request.user)
    org = request.user.organization

    direction = None
    if direction_id:
        direction = get_object_or_404(Direction, id=direction_id, organization=org)

    # Users pour dropdown directeur
    from apps.accounts.models import User
    users = User.objects.filter(organization=org, is_active=True)

    if request.method == "POST":
        code = (request.POST.get("code") or "").strip().upper()
        name = (request.POST.get("name") or "").strip()
        description = (request.POST.get("description") or "").strip()
        director_id = request.POST.get("director") or None
        is_achats = request.POST.get("is_achats") == "on"
        is_active = request.POST.get("is_active") == "on"
        display_order = request.POST.get("display_order") or 0

        try:
            display_order = int(display_order)
        except ValueError:
            display_order = 0

        if not code or not name:
            messages.error(request, "Le code et le nom sont obligatoires.")
            return render(request, "da/admin/direction_form.html", {
                "direction": direction, "users": users,
            })

        director = None
        if director_id:
            director = User.objects.filter(id=director_id, organization=org).first()

        if direction:
            direction.code = code
            direction.name = name
            direction.description = description
            direction.director = director
            direction.is_achats = is_achats
            direction.is_active = is_active
            direction.display_order = display_order
            direction.save()
            messages.success(request, f"Direction « {name} » mise a jour.")
        else:
            Direction.objects.create(
                organization=org,
                code=code, name=name, description=description,
                director=director, is_achats=is_achats,
                is_active=is_active, display_order=display_order,
            )
            messages.success(request, f"Direction « {name} » creee.")

        return redirect("da_admin_directions")

    return render(request, "da/admin/direction_form.html", {
        "direction": direction, "users": users,
    })


@login_required
@require_POST
def admin_direction_delete(request, direction_id):
    """Supprime une direction (si pas de services)."""
    _require_admin_da(request.user)
    direction = get_object_or_404(
        Direction, id=direction_id, organization=request.user.organization,
    )
    if direction.services.exists():
        messages.error(request, f"Impossible : {direction.services.count()} service(s) rattache(s).")
        return redirect("da_admin_directions")
    name = direction.name
    direction.delete()
    messages.success(request, f"Direction « {name} » supprimee.")
    return redirect("da_admin_directions")


@login_required
def admin_services(request):
    """Liste des services."""
    _require_admin_da(request.user)
    org = request.user.organization

    services = Service.objects.filter(organization=org).select_related("direction").order_by(
        "direction__display_order", "display_order", "name",
    )

    return render(request, "da/admin/services.html", {"services": services})


@login_required
def admin_service_form(request, service_id=None):
    """Creer / modifier un service."""
    _require_admin_da(request.user)
    org = request.user.organization

    service = None
    if service_id:
        service = get_object_or_404(Service, id=service_id, organization=org)

    directions = Direction.objects.filter(organization=org, is_active=True)
    from apps.accounts.models import User
    users = User.objects.filter(organization=org, is_active=True)

    if request.method == "POST":
        code = (request.POST.get("code") or "").strip().upper()
        name = (request.POST.get("name") or "").strip()
        direction_id = request.POST.get("direction")
        chief_id = request.POST.get("chief") or None
        is_active = request.POST.get("is_active") == "on"
        display_order = request.POST.get("display_order") or 0

        try:
            display_order = int(display_order)
        except ValueError:
            display_order = 0

        if not code or not name or not direction_id:
            messages.error(request, "Code, nom et direction sont obligatoires.")
            return render(request, "da/admin/service_form.html", {
                "service": service, "directions": directions, "users": users,
            })

        direction = get_object_or_404(Direction, id=direction_id, organization=org)
        chief = None
        if chief_id:
            chief = User.objects.filter(id=chief_id, organization=org).first()

        if service:
            service.code = code
            service.name = name
            service.direction = direction
            service.chief = chief
            service.is_active = is_active
            service.display_order = display_order
            service.save()
            messages.success(request, f"Service « {name} » mis a jour.")
        else:
            Service.objects.create(
                organization=org,
                code=code, name=name, direction=direction,
                chief=chief, is_active=is_active, display_order=display_order,
            )
            messages.success(request, f"Service « {name} » cree.")

        return redirect("da_admin_services")

    return render(request, "da/admin/service_form.html", {
        "service": service, "directions": directions, "users": users,
    })


@login_required
@require_POST
def admin_service_delete(request, service_id):
    """Supprime un service."""
    _require_admin_da(request.user)
    service = get_object_or_404(
        Service, id=service_id, organization=request.user.organization,
    )
    name = service.name
    service.delete()
    messages.success(request, f"Service « {name} » supprime.")
    return redirect("da_admin_services")
