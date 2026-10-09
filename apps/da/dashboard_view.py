"""Vue Dashboard DA enrichi (KPIs + charts + filtres)."""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q, Avg, F
from django.db.models.functions import TruncDate, TruncMonth
from django.shortcuts import render
from django.utils import timezone

from .models import (
    PurchaseRequest, PurchaseRequestItem, DAItem,
    DACategory, DAStockMovement, DASignatureFlow,
)
from apps.organizations.models import Direction, Service


@login_required
def da_dashboard(request):
    """Dashboard DA avec KPIs + graphiques + filtres."""
    org = request.user.organization
    now = timezone.now()

    # ─── Filtres ───
    period = request.GET.get("period", "30")
    try:
        days = int(period)
    except ValueError:
        days = 30

    direction_id = request.GET.get("direction", "")
    service_id = request.GET.get("service", "")
    status_filter = request.GET.get("status", "")

    start_date = now - timedelta(days=days)

    # ─── Base queryset ───
    qs = PurchaseRequest.objects.filter(organization=org)

    if direction_id:
        qs = qs.filter(service__direction_id=direction_id)
    if service_id:
        qs = qs.filter(service_id=service_id)
    if status_filter:
        qs = qs.filter(status=status_filter)

    qs_period = qs.filter(created_at__gte=start_date)

    # ─── KPIs ───
    my_requests = qs.filter(requester=request.user)
    pending_my_action = DASignatureFlow.objects.filter(
        purchase_request__organization=org,
        assigned_to=request.user,
        status="PENDING",
    )

    kpis = {
        "total": qs.count(),
        "total_period": qs_period.count(),
        "in_progress": qs.filter(status__in=[
            "SOUMISE", "VISEE_DIRECTEUR", "STOCK_VERIFIE",
            "VALIDEE", "COMMANDEE",
        ]).count(),
        "closed_period": qs_period.filter(status="CLOTUREE").count(),
        "pending_me": pending_my_action.count(),
        "total_amount": qs.filter(
            status__in=["VALIDEE", "COMMANDEE", "RECUE", "RECUE_PARTIELLE", "CLOTUREE"],
        ).aggregate(s=Sum("total_amount"))["s"] or Decimal("0"),
        "total_amount_period": qs_period.filter(
            status__in=["VALIDEE", "COMMANDEE", "RECUE", "RECUE_PARTIELLE", "CLOTUREE"],
        ).aggregate(s=Sum("total_amount"))["s"] or Decimal("0"),
        "avg_amount": qs_period.aggregate(a=Avg("total_amount"))["a"] or Decimal("0"),
        "rejection_rate": 0,
    }

    # Taux de refus
    total_closed = qs_period.filter(status__in=["CLOTUREE", "REFUSEE"]).count()
    rejected = qs_period.filter(status="REFUSEE").count()
    if total_closed:
        kpis["rejection_rate"] = round((rejected / total_closed) * 100, 1)

    # ─── Graphique : évolution jour par jour ───
    daily_qs = (
        qs_period
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(count=Count("id"), amount=Sum("total_amount"))
        .order_by("day")
    )
    daily = [
        {
            "day": d["day"].strftime("%d/%m"),
            "count": d["count"],
            "amount": float(d["amount"] or 0),
        }
        for d in daily_qs
    ]

    # ─── Graphique : top 5 articles demandes ───
    top_items = (
        PurchaseRequestItem.objects
        .filter(
            request__organization=org,
            request__created_at__gte=start_date,
            request__status__in=["VALIDEE", "COMMANDEE", "RECUE", "CLOTUREE", "RECUE_PARTIELLE"],
        )
        .values("item__name")
        .annotate(
            total_qty=Sum("quantity"),
            total_amount=Sum(F("quantity") * F("unit_price")),
        )
        .order_by("-total_qty")[:5]
    )
    top_items_data = [
        {
            "name": item["item__name"][:35],
            "qty": item["total_qty"] or 0,
            "amount": float(item["total_amount"] or 0),
        }
        for item in top_items
    ]

    # ─── Repartition par statut (pie) ───
    status_distribution = (
        qs_period
        .values("status")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    status_data = [
        {
            "status": s["status"],
            "label": dict(PurchaseRequest.STATUS_CHOICES).get(s["status"], s["status"]),
            "count": s["count"],
        }
        for s in status_distribution
    ]

    # ─── Top 5 directions ───
    top_directions = (
        qs_period
        .values("service__direction__code", "service__direction__name")
        .annotate(
            count=Count("id"),
            amount=Sum("total_amount"),
        )
        .order_by("-amount")[:5]
    )
    top_dir_data = [
        {
            "code": d["service__direction__code"] or "N/A",
            "name": d["service__direction__name"] or "Sans direction",
            "count": d["count"],
            "amount": float(d["amount"] or 0),
        }
        for d in top_directions
    ]

    # ─── Listes ───
    recent_requests = qs.order_by("-created_at")[:10]
    pending_list = pending_my_action.select_related(
        "purchase_request", "purchase_request__requester", "purchase_request__service",
    )[:10]

    # ─── Alertes stock ───
    low_stock_items = DAItem.objects.filter(
        organization=org, is_active=True,
    ).filter(
        Q(stock_quantity=0) | Q(stock_quantity__lte=F("reorder_level")),
    ).order_by("stock_quantity")[:10]

    # ─── Filtres disponibles ───
    all_directions = Direction.objects.filter(organization=org, is_active=True)
    all_services = Service.objects.filter(organization=org, is_active=True)

    context = {
        "kpis": kpis,
        "daily": daily,
        "top_items": top_items_data,
        "status_data": status_data,
        "top_directions": top_dir_data,
        "recent_requests": recent_requests,
        "pending_list": pending_list,
        "low_stock_items": low_stock_items,
        "all_directions": all_directions,
        "all_services": all_services,
        "filters": {
            "period": days,
            "direction": direction_id,
            "service": service_id,
            "status": status_filter,
        },
        "statuses": PurchaseRequest.STATUS_CHOICES,
    }
    return render(request, "da/dashboard.html", context)
