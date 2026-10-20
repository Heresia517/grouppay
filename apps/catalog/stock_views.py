"""Vues stock avancé — historique + alertes + ajustement."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Sum, Q
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Product, StockMovement, StockAlert


def _require_manager(user):
    if user.role not in ("ADMIN", "GESTIONNAIRE", "FOURNISSEUR"):
        raise PermissionDenied("Réservé aux gestionnaires")


@login_required
def stock_dashboard(request):
    """Dashboard mouvements + alertes."""
    _require_manager(request.user)
    org = request.user.organization

    # Filtres
    product_id = request.GET.get("product")
    type_filter = request.GET.get("type")
    period = request.GET.get("period", "30")
    try:
        days = int(period)
    except ValueError:
        days = 30
    start = timezone.now() - timezone.timedelta(days=days)

    qs = StockMovement.objects.filter(
        organization=org, created_at__gte=start,
    ).select_related("product", "actor", "order")

    if product_id:
        qs = qs.filter(product_id=product_id)
    if type_filter:
        qs = qs.filter(movement_type=type_filter)

    # KPIs
    products = Product.objects.filter(organization=org, is_active=True)
    low_stock = products.filter(stock_quantity__gt=0, stock_quantity__lte=10)
    out_of_stock = products.filter(stock_quantity=0)
    active_alerts = StockAlert.objects.filter(organization=org, is_resolved=False)

    context = {
        "movements": qs[:200],
        "products": products.order_by("name"),
        "alerts": active_alerts.select_related("product")[:50],
        "kpis": {
            "low_stock_count": low_stock.count(),
            "out_of_stock_count": out_of_stock.count(),
            "active_alerts": active_alerts.count(),
            "total_movements": qs.count(),
        },
        "filters": {
            "product": product_id or "",
            "type": type_filter or "",
            "period": days,
        },
        "movement_types": StockMovement.TYPE_CHOICES,
    }
    return render(request, "catalog/stock_dashboard.html", context)


@login_required
def product_stock_history(request, product_id):
    """Historique stock avec isolation fournisseur."""
    from django.shortcuts import get_object_or_404, render
    from .models import Product, StockMovement
    
    # Filtre : si FOURNISSEUR, il ne voit QUE ses propres produits
    qs = Product.objects.filter(organization=request.user.organization)
    if request.user.role == "FOURNISSEUR":
        qs = qs.filter(supplier=request.user)
    
    product = get_object_or_404(qs, id=product_id)
    movements = StockMovement.objects.filter(product=product).order_by("-created_at")[:50]
    
    return render(request, "catalog/stock_history.html", {
        "product": product,
        "movements": movements,
    })

def adjust_stock(request, product_id):
    """Ajustement manuel du stock (inventaire, casse, etc.)."""
    _require_manager(request.user)
    product = get_object_or_404(Product, id=product_id, organization=request.user.organization)

    try:
        new_qty = int(request.POST.get("new_quantity", 0))
    except (TypeError, ValueError):
        messages.error(request, "Quantité invalide")
        return redirect("stock_dashboard")

    if new_qty < 0:
        messages.error(request, "Le stock ne peut pas être négatif")
        return redirect("stock_dashboard")

    reason = (request.POST.get("reason") or "").strip() or "Ajustement manuel"

    with transaction.atomic():
        stock_before = product.stock_quantity
        delta = new_qty - stock_before
        product.stock_quantity = new_qty
        product.save(update_fields=["stock_quantity"])

        if delta != 0:
            StockMovement.objects.create(
                organization=product.organization,
                product=product,
                movement_type="ADJUST",
                quantity=delta,
                stock_before=stock_before,
                stock_after=new_qty,
                reason=reason,
                actor=request.user,
            )

        # Alerte si passe sous le seuil
        if stock_before > product.reorder_level >= new_qty:
            StockAlert.objects.create(
                organization=product.organization,
                product=product,
                stock_at_alert=new_qty,
                reorder_level=product.reorder_level,
            )

    messages.success(request, f"Stock ajusté : {stock_before} → {new_qty}")
    return redirect("stock_dashboard")


@login_required
@require_POST
def resolve_alert(request, alert_id):
    """Marque une alerte comme résolue."""
    _require_manager(request.user)
    alert = get_object_or_404(StockAlert, id=alert_id, organization=request.user.organization)
    alert.is_resolved = True
    alert.resolved_at = timezone.now()
    alert.save(update_fields=["is_resolved", "resolved_at"])
    return redirect("stock_dashboard")
