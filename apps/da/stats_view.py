"""Vue Statistiques avancees DA."""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Sum, Count, Avg, Q, F
from django.db.models.functions import TruncMonth, TruncWeek, TruncDay
from django.shortcuts import render
from django.utils import timezone

from .models import PurchaseRequest, PurchaseRequestItem, DAItem
from apps.organizations.models import Direction, Service


def _require_admin_da(user):
    if user.role == "ADMIN" or user.is_dg:
        return True
    if user.service and user.service.direction.is_achats:
        return True
    if user.is_director and user.directed_directions.filter(is_achats=True).exists():
        return True
    raise PermissionDenied("Reserve aux administrateurs DA")


@login_required
def da_stats(request):
    """Statistiques avancees."""
    _require_admin_da(request.user)
    org = request.user.organization
    now = timezone.now()

    # Periode
    period = request.GET.get("period", "90")
    try:
        days = int(period)
    except ValueError:
        days = 90
    start = now - timedelta(days=days)

    qs = PurchaseRequest.objects.filter(organization=org, created_at__gte=start)
    qs_valid = qs.filter(status__in=["VALIDEE", "COMMANDEE", "RECUE", "RECUE_PARTIELLE", "CLOTUREE"])

    # ─── KPIs avances ───
    kpis = {
        "total": qs.count(),
        "total_amount": qs_valid.aggregate(s=Sum("total_amount"))["s"] or Decimal("0"),
        "avg_amount": qs_valid.aggregate(a=Avg("total_amount"))["a"] or Decimal("0"),
        "max_amount": qs_valid.aggregate(m=models.Max("total_amount"))["m"] or Decimal("0"),
        "avg_processing_days": 0,
        "rejection_rate": 0,
        "avg_items_per_da": 0,
    }

    # Delai moyen de traitement
    closed = qs.filter(status="CLOTUREE", received_at__isnull=False)
    if closed.exists():
        deltas = [(r.received_at - r.created_at).days for r in closed if r.received_at]
        if deltas:
            kpis["avg_processing_days"] = round(sum(deltas) / len(deltas), 1)

    # Taux de refus
    total_decided = qs.filter(status__in=["CLOTUREE", "REFUSEE"]).count()
    if total_decided:
        rejected = qs.filter(status="REFUSEE").count()
        kpis["rejection_rate"] = round((rejected / total_decided) * 100, 1)

    # Items par DA
    total_items = PurchaseRequestItem.objects.filter(request__in=qs).count()
    if qs.count():
        kpis["avg_items_per_da"] = round(total_items / qs.count(), 1)

    # ─── Evolution mensuelle (12 derniers mois) ───
    twelve_months_ago = now - timedelta(days=365)
    monthly_qs = (
        PurchaseRequest.objects
        .filter(organization=org, created_at__gte=twelve_months_ago)
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(
            count=Count("id"),
            amount=Sum("total_amount", filter=Q(status__in=["VALIDEE", "COMMANDEE", "RECUE", "CLOTUREE", "RECUE_PARTIELLE"])),
        )
        .order_by("month")
    )
    monthly_data = [
        {
            "month": m["month"].strftime("%b %Y"),
            "count": m["count"],
            "amount": float(m["amount"] or 0),
        }
        for m in monthly_qs
    ]

    # ─── Repartition par statut ───
    status_breakdown = (
        qs.values("status")
        .annotate(count=Count("id"), amount=Sum("total_amount"))
        .order_by("-count")
    )
    status_data = [
        {
            "status": s["status"],
            "label": dict(PurchaseRequest.STATUS_CHOICES).get(s["status"], s["status"]),
            "count": s["count"],
            "amount": float(s["amount"] or 0),
        }
        for s in status_breakdown
    ]

    # ─── Top 10 utilisateurs (demandeurs) ───
    top_users = (
        qs.values("requester__email", "requester__first_name", "requester__last_name")
        .annotate(
            count=Count("id"),
            amount=Sum("total_amount"),
        )
        .order_by("-count")[:10]
    )
    top_users_data = [
        {
            "email": u["requester__email"],
            "name": f"{u['requester__first_name'] or ''} {u['requester__last_name'] or ''}".strip() or u["requester__email"],
            "count": u["count"],
            "amount": float(u["amount"] or 0),
        }
        for u in top_users
    ]

    # ─── Top 10 articles (quantite + montant) ───
    top_items_qs = (
        PurchaseRequestItem.objects
        .filter(request__in=qs)
        .values("item__name", "item__category__name")
        .annotate(
            total_qty=Sum("quantity"),
            total_amount=Sum(F("quantity") * F("unit_price")),
        )
        .order_by("-total_qty")[:10]
    )
    top_items_data = [
        {
            "name": item["item__name"],
            "category": item["item__category__name"],
            "qty": item["total_qty"] or 0,
            "amount": float(item["total_amount"] or 0),
        }
        for item in top_items_qs
    ]

    # ─── Repartition par direction ───
    by_direction = (
        qs.values("service__direction__code", "service__direction__name")
        .annotate(count=Count("id"), amount=Sum("total_amount"))
        .order_by("-amount")
    )
    direction_data = [
        {
            "code": d["service__direction__code"] or "N/A",
            "name": d["service__direction__name"] or "Sans direction",
            "count": d["count"],
            "amount": float(d["amount"] or 0),
        }
        for d in by_direction
    ]

    # ─── Repartition par service ───
    by_service = (
        qs.values("service__code", "service__name")
        .annotate(count=Count("id"), amount=Sum("total_amount"))
        .order_by("-amount")[:15]
    )
    service_data = [
        {
            "code": s["service__code"] or "—",
            "name": s["service__name"] or "Sans service",
            "count": s["count"],
            "amount": float(s["amount"] or 0),
        }
        for s in by_service
    ]

    # ─── Statuts de stock (health) ───
    items_all = DAItem.objects.filter(organization=org, is_active=True)
    stock_health = {
        "healthy": items_all.filter(stock_quantity__gt=F("reorder_level")).count(),
        "low": items_all.filter(stock_quantity__lte=F("reorder_level"), stock_quantity__gt=0).count(),
        "out": items_all.filter(stock_quantity=0).count(),
        "total": items_all.count(),
    }

    context = {
        "kpis": kpis,
        "monthly_data": monthly_data,
        "status_data": status_data,
        "top_users": top_users_data,
        "top_items": top_items_data,
        "direction_data": direction_data,
        "service_data": service_data,
        "stock_health": stock_health,
        "period": days,
    }
    return render(request, "da/stats.html", context)


from django.db import models  # noqa
