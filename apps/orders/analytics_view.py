"""Vue Analytics membre : stats personnelles commandes."""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Avg, Q, F
from django.db.models.functions import TruncMonth
from django.shortcuts import render
from django.utils import timezone

from apps.orders.models import Order, OrderItem, Cart
from apps.catalog.models import Product, Review


@login_required
def member_analytics(request):
    """Dashboard analytics personnel pour un membre."""
    user = request.user
    org = user.organization
    now = timezone.now()

    # Filtre periode
    period = request.GET.get("period", "365")
    try:
        days = int(period)
    except ValueError:
        days = 365
    start = now - timedelta(days=days)

    # ─── Toutes les commandes du membre ───
    orders_all = Order.objects.filter(member=user, organization=org)
    orders = orders_all.filter(created_at__gte=start)
    valid_orders = orders.filter(status__in=["VALIDEE", "EN_LIVRAISON", "LIVREE"])
    orders_all_valid = orders_all.filter(status__in=["VALIDEE", "EN_LIVRAISON", "LIVREE"])

    # ─── KPIs ───
    total_spent = orders_all_valid.aggregate(s=Sum("total_amount"))["s"] or Decimal("0")
    total_spent_period = valid_orders.aggregate(s=Sum("total_amount"))["s"] or Decimal("0")
    total_orders = orders_all.count()
    orders_period = orders.count()
    delivered = orders_all.filter(status="LIVREE").count()
    pending = orders_all.filter(status="EN_ATTENTE_VALIDATION").count()

    avg_basket = valid_orders.aggregate(a=Avg("total_amount"))["a"] or Decimal("0")

    # Estimation economies (15% vs prix normal)
    savings = float(total_spent) * 0.15

    # ─── Evolution mensuelle ───
    twelve_months = now - timedelta(days=365)
    monthly_qs = (
        orders_all_valid.filter(created_at__gte=twelve_months)
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(count=Count("id"), amount=Sum("total_amount"))
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

    # ─── Top categories achetees ───
    top_categories = (
        OrderItem.objects.filter(
            order__member=user,
            order__organization=org,
            order__status__in=["VALIDEE", "EN_LIVRAISON", "LIVREE"],
        )
        .values("product__category__name")
        .annotate(
            total_qty=Sum("quantity"),
            total_amount=Sum(F("quantity") * F("unit_price")),
        )
        .order_by("-total_amount")[:5]
    )
    categories_data = [
        {
            "name": c["product__category__name"] or "Sans categorie",
            "qty": c["total_qty"] or 0,
            "amount": float(c["total_amount"] or 0),
        }
        for c in top_categories
    ]

    # ─── Top produits achetes ───
    top_products = (
        OrderItem.objects.filter(
            order__member=user,
            order__organization=org,
            order__status__in=["VALIDEE", "EN_LIVRAISON", "LIVREE"],
        )
        .values("product__name", "product__id")
        .annotate(
            total_qty=Sum("quantity"),
            total_amount=Sum(F("quantity") * F("unit_price")),
        )
        .order_by("-total_qty")[:5]
    )
    products_data = [
        {
            "name": p["product__name"],
            "id": p["product__id"],
            "qty": p["total_qty"] or 0,
            "amount": float(p["total_amount"] or 0),
        }
        for p in top_products
    ]

    # ─── Commandes recentes ───
    recent_orders = orders_all.select_related("organization").order_by("-created_at")[:5]

    # ─── Panier actuel ───
    current_cart = Cart.objects.filter(user=user, status="OPEN").first()
    cart_items_count = current_cart.items.count() if current_cart else 0
    cart_amount = Decimal("0")
    if current_cart:
        for item in current_cart.items.select_related("product"):
            cart_amount += item.product.price * item.quantity

    # ─── Stats avis ───
    reviews_count = Review.objects.filter(member=user, is_published=True).count()

    context = {
        "kpis": {
            "total_spent": total_spent,
            "total_spent_period": total_spent_period,
            "total_orders": total_orders,
            "orders_period": orders_period,
            "delivered": delivered,
            "pending": pending,
            "avg_basket": avg_basket,
            "savings": savings,
            "reviews_count": reviews_count,
            "cart_items_count": cart_items_count,
            "cart_amount": cart_amount,
        },
        "monthly_data": monthly_data,
        "categories_data": categories_data,
        "products_data": products_data,
        "recent_orders": recent_orders,
        "period": days,
    }
    return render(request, "mutuelle/member_analytics.html", context)
