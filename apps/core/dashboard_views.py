"""Dashboard dispatcher : rend le bon template selon rôle + flags."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from apps.orders.models import Order, OrderItem


def _scope_orders(user):
    """Retourne le queryset des commandes visibles par l'utilisateur."""
    qs = Order.objects.filter(organization=user.organization)
    if user.is_dg or user.role == "ADMIN":
        return qs
    if user.is_director and getattr(user, "directed_directions", None):
        dir_ids = list(user.directed_directions.values_list("id", flat=True))
        return qs.filter(member__service__direction_id__in=dir_ids)
    if user.is_service_chief and user.service_id:
        return qs.filter(member__service_id=user.service_id)
    if user.role == "GESTIONNAIRE":
        return qs
    return qs.filter(member=user)


def _scope_members(user):
    """Retourne les membres du périmètre de l'utilisateur."""
    from apps.accounts.models import User
    qs = User.objects.filter(organization=user.organization)
    if user.is_dg or user.role == "ADMIN":
        return qs
    if user.is_director and getattr(user, "directed_directions", None):
        dir_ids = list(user.directed_directions.values_list("id", flat=True))
        return qs.filter(service__direction_id__in=dir_ids)
    if user.is_service_chief and user.service_id:
        return qs.filter(service_id=user.service_id)
    return qs.none()


@login_required
def dashboard(request):
    """Point d'entrée unique : dispatche selon le rôle."""
    u = request.user
    org = u.organization

    # ─── ADMIN / DG
    if u.is_dg or u.role == "ADMIN":
        orders = _scope_orders(u)
        ctx = {
            "scope": "admin",
            "scope_label": "Direction Générale",
            "total_orders": orders.count(),
            "pending_orders": orders.filter(status="EN_ATTENTE_VALIDATION").count(),
            "total_members": _scope_members(u).count(),
            "total_directions": org.directions.count() if hasattr(org, "directions") else 0,
            "total_services": org.services.count() if hasattr(org, "services") else 0,
            "recent_orders": orders.order_by("-created_at")[:10],
        }
        return render(request, "dashboard/admin.html", ctx)

    # ─── DIRECTEUR (GESTIONNAIRE + is_director)
    if u.is_director:
        orders = _scope_orders(u)
        dirs = list(u.directed_directions.all()) if hasattr(u, "directed_directions") else []
        ctx = {
            "scope": "director",
            "scope_label": f"Direction : {dirs[0].name if dirs else '—'}",
            "directions": dirs,
            "services": [s for d in dirs for s in d.services.all()],
            "total_orders": orders.count(),
            "pending_orders": orders.filter(status="EN_ATTENTE_VALIDATION").count(),
            "total_members": _scope_members(u).count(),
            "recent_orders": orders.order_by("-created_at")[:10],
        }
        return render(request, "dashboard/director.html", ctx)

    # ─── CHEF DE SERVICE (MEMBRE + is_service_chief)
    if u.is_service_chief:
        orders = _scope_orders(u)
        ctx = {
            "scope": "chief",
            "scope_label": f"Service : {u.service.name if u.service else '—'}",
            "service": u.service,
            "total_orders": orders.count(),
            "pending_orders": orders.filter(status="EN_ATTENTE_VALIDATION").count(),
            "total_members": _scope_members(u).count(),
            "recent_orders": orders.order_by("-created_at")[:10],
        }
        return render(request, "dashboard/chief.html", ctx)

    # ─── RH / GESTIONNAIRE (sans flag)
    if u.role == "GESTIONNAIRE":
        # Réutilise la vue rh_dashboard existante
        from apps.orders.dashboard_views import rh_dashboard
        return rh_dashboard(request)

    # ─── LIVREUR
    if u.role == "LIVREUR":
        try:
            from apps.deliveries.models import Delivery
            deliveries = Delivery.objects.filter(courier=u).order_by("-created_at")
            ctx = {
                "scope": "courier",
                "scope_label": "Mes livraisons",
                "deliveries_todo": deliveries.filter(status__in=["ASSIGNEE", "EN_COURS"]).count(),
                "deliveries_done": deliveries.filter(status="LIVREE").count(),
                "recent_deliveries": deliveries[:10],
            }
        except Exception:
            ctx = {"scope": "courier", "scope_label": "Mes livraisons"}
        return render(request, "dashboard/courier.html", ctx)

    # ─── FOURNISSEUR
    if u.role == "FOURNISSEUR":
        try:
            from apps.catalog.models import Product
            products = Product.objects.filter(supplier=u)
            ctx = {
                "scope": "supplier",
                "scope_label": "Mon espace fournisseur",
                "my_products": products.count(),
                "private_products": products.filter(is_supplier_private=True).count(),
                "recent_products": products.order_by("-created_at")[:10],
            }
        except Exception:
            ctx = {"scope": "supplier", "scope_label": "Mon espace fournisseur"}
        return render(request, "dashboard/supplier.html", ctx)

    # ─── MEMBRE (par défaut)
    my_orders = Order.objects.filter(organization=org, member=u).order_by("-created_at")
    ctx = {
        "scope": "member",
        "scope_label": "Mon espace",
        "my_orders": my_orders[:10],
        "total_orders": my_orders.count(),
        "pending_orders": my_orders.filter(status="EN_ATTENTE_VALIDATION").count(),
        "delivered_orders": my_orders.filter(status="LIVREE").count(),
    }
    return render(request, "dashboard/member.html", ctx)
