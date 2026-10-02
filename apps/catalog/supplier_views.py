"""Dashboard fournisseur — mes produits + commandes reçues."""
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Sum, Count
from django.shortcuts import render

from .models import Product
from apps.orders.models import OrderItem


def _require_supplier(user):
    if user.role not in ("FOURNISSEUR", "ADMIN", "GESTIONNAIRE"):
        raise PermissionDenied("Réservé aux fournisseurs")


@login_required
def supplier_dashboard(request):
    """Tour de contrôle du fournisseur."""
    _require_supplier(request.user)
    org = request.user.organization

    # Mes produits
    products = Product.objects.filter(
        organization=org,
        supplier=request.user,
        is_active=True,
    ).select_related("category")

    # Stats produits
    products_stats = {
        "total": products.count(),
        "active": products.filter(is_active=True).count(),
        "out_of_stock": products.filter(stock_quantity=0).count(),
        "low_stock": products.filter(stock_quantity__gt=0, stock_quantity__lte=10).count(),
    }

    # Commandes reçues (OrderItems liés à mes produits)
    order_items = OrderItem.objects.filter(
        product__supplier=request.user,
        product__organization=org,
    ).select_related("order", "order__member", "product")

    # Ventes validées
    valid_orders = order_items.filter(
        order__status__in=["VALIDEE", "EN_LIVRAISON", "LIVREE"],
    )
    sales_stats = {
        "total_items": valid_orders.count(),
        "revenue": sum(
            (item.unit_price * item.quantity for item in valid_orders),
            start=0,
        ),
        "pending_count": order_items.filter(order__status="EN_ATTENTE_VALIDATION").count(),
    }

    # Top produits
    top = (
        valid_orders
        .values("product__name")
        .annotate(qty=Sum("quantity"))
        .order_by("-qty")[:5]
    )

    context = {
        "products": products[:50],
        "products_stats": products_stats,
        "sales_stats": sales_stats,
        "recent_items": order_items.order_by("-order__created_at")[:20],
        "top_products": list(top),
    }
    return render(request, "catalog/supplier_dashboard.html", context)
