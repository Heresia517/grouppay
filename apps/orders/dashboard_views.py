from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Sum, Count, Avg, Q
from django.db.models.functions import TruncDate
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Order, OrderItem
from .services import validate_order, reject_order
from apps.catalog.services import check_low_stock


def _require_rh(user):
    if user.role not in ("ADMIN", "GESTIONNAIRE"):
        raise PermissionDenied("Accès réservé aux RH / Admin")


def _pct_delta(current, previous):
    """Calcule la variation en % entre 2 valeurs."""
    if not previous:
        return None
    try:
        return round(((float(current) - float(previous)) / float(previous)) * 100, 1)
    except (ZeroDivisionError, TypeError):
        return None


@login_required
def rh_dashboard(request):
    """Dashboard RH — KPIs, charts, bulk validation."""
    _require_rh(request.user)
    org = request.user.organization
    now = timezone.now()

    # Période choisie
    period = request.GET.get("period", "30")
    try:
        days = int(period)
    except ValueError:
        days = 30
    if days not in (7, 30, 90):
        days = 30

    start_current = now - timedelta(days=days)
    start_previous = start_current - timedelta(days=days)

    qs = Order.objects.filter(organization=org)
    qs_valid = qs.filter(status__in=["VALIDEE", "EN_LIVRAISON", "LIVREE"])

    # ─── KPIs période courante
    current = qs_valid.filter(created_at__gte=start_current)
    previous = qs_valid.filter(created_at__gte=start_previous, created_at__lt=start_current)

    revenue_current = current.aggregate(s=Sum("total_amount"))["s"] or 0
    revenue_previous = previous.aggregate(s=Sum("total_amount"))["s"] or 0

    orders_current = current.count()
    orders_previous = previous.count()

    avg_current = current.aggregate(a=Avg("total_amount"))["a"] or 0
    avg_previous = previous.aggregate(a=Avg("total_amount"))["a"] or 0

    pending_count = qs.filter(status="EN_ATTENTE_VALIDATION").count()

    kpis = {
        "revenue": {
            "value": revenue_current,
            "delta": _pct_delta(revenue_current, revenue_previous),
        },
        "orders": {
            "value": orders_current,
            "delta": _pct_delta(orders_current, orders_previous),
        },
        "avg_basket": {
            "value": avg_current,
            "delta": _pct_delta(avg_current, avg_previous),
        },
        "pending": pending_count,
    }

    # ─── Évolution jour par jour
    daily_qs = (
        current
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(count=Count("id"), revenue=Sum("total_amount"))
        .order_by("day")
    )
    daily = [
        {
            "day": d["day"].strftime("%d/%m"),
            "count": d["count"],
            "revenue": float(d["revenue"] or 0),
        }
        for d in daily_qs
    ]

    # ─── Top 5 produits
    top_products = list(
        OrderItem.objects.filter(
            order__organization=org,
            order__status__in=["VALIDEE", "EN_LIVRAISON", "LIVREE"],
            order__created_at__gte=start_current,
        )
        .values("product__name")
        .annotate(qty=Sum("quantity"), ca=Sum("unit_price"))
        .order_by("-qty")[:5]
    )
    top_products_data = [
        {"name": p["product__name"][:35], "qty": p["qty"] or 0}
        for p in top_products
    ]

    # ─── Alertes stock
    low_stock = check_low_stock(org)

    # ─── Commandes en attente
    pending_orders = list(
        qs.filter(status="EN_ATTENTE_VALIDATION")
        .select_related("member")
        .order_by("-created_at")[:30]
    )

    context = {
        "kpis": kpis,
        "daily": daily,
        "top_products_data": top_products_data,
        "low_stock": low_stock,
        "pending_orders": pending_orders,
        "period": days,
    }
    return render(request, "admin/dashboard.html", context)


@login_required
@require_POST
def bulk_validate_orders(request):
    """Valide plusieurs commandes en 1 clic."""
    _require_rh(request.user)
    ids = request.POST.getlist("order_ids")
    for oid in ids:
        try:
            order = Order.objects.get(id=oid, organization=request.user.organization)
            validate_order(order, actor=request.user)
        except Exception:
            pass
    return redirect("rh_dashboard")


@login_required
@require_POST
def bulk_reject_orders(request):
    """Refuse plusieurs commandes en 1 clic."""
    _require_rh(request.user)
    ids = request.POST.getlist("order_ids")
    reason = request.POST.get("reason", "").strip() or "Refus en masse"
    for oid in ids:
        try:
            order = Order.objects.get(id=oid, organization=request.user.organization)
            reject_order(order, actor=request.user, reason=reason)
        except Exception:
            pass
    return redirect("rh_dashboard")
