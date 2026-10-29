"""PACK A3 — SMS + Emails enrichis + Dashboard fournisseur."""
from pathlib import Path
ROOT = Path.cwd()

def patch(path, old, new, label):
    p = ROOT / path
    if not p.exists():
        print(f"  ✗ {path} introuvable"); return False
    src = p.read_text(encoding="utf-8")
    if old not in src:
        if new[:50] in src: print(f"  ℹ {label} déjà patché"); return True
        print(f"  ⚠ {label} : pattern introuvable"); return False
    p.write_text(src.replace(old, new, 1), encoding="utf-8")
    print(f"  ✓ {label}"); return True

def write(path, content, label):
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    print(f"  ✓ {label}")

# ═══════════════════════════════════════════════════════════════
# 1. SMS Service (Africa's Talking / console fallback)
# ═══════════════════════════════════════════════════════════════
write("apps/notifications/sms_service.py", '''"""Service SMS — Africa's Talking avec fallback console."""
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def send_sms(phone, message):
    """Envoie un SMS. Fallback console si pas de config."""
    if not phone:
        return False

    try:
        username = getattr(settings, "AFRICASTALKING_USERNAME", "")
        api_key = getattr(settings, "AFRICASTALKING_API_KEY", "")

        if username and api_key:
            import africastalking
            africastalking.initialize(username, api_key)
            sms = africastalking.SMS
            response = sms.send(message, [phone])
            logger.info(f"[SMS] Sent to {phone}: {response}")
            return True
        else:
            # Console fallback (dev)
            print(f"\\n📱 [SMS to {phone}]: {message}\\n")
            return True
    except Exception as e:
        logger.warning(f"[SMS] Failed for {phone}: {e}")
        return False


def send_order_validated_sms(order):
    """SMS court : commande validée."""
    phone = getattr(order.member, "phone", "") or ""
    if not phone:
        return False
    msg = f"ZionPay: commande {order.order_number} VALIDEE ({order.total_amount} {order.currency_code})."
    return send_sms(phone, msg)


def send_order_delivered_sms(order):
    """SMS court : commande livrée."""
    phone = getattr(order.member, "phone", "") or ""
    if not phone:
        return False
    msg = f"ZionPay: commande {order.order_number} LIVREE. Merci !"
    return send_sms(phone, msg)


def send_order_rejected_sms(order, reason=""):
    """SMS court : commande refusée."""
    phone = getattr(order.member, "phone", "") or ""
    if not phone:
        return False
    msg = f"ZionPay: commande {order.order_number} REFUSEE. Motif: {reason[:80]}"
    return send_sms(phone, msg)
''', "apps/notifications/sms_service.py")

# ═══════════════════════════════════════════════════════════════
# 2. Templates emails additionnels
# ═══════════════════════════════════════════════════════════════
write("templates/emails/order_rejected.html", '''<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="font-family:Inter,system-ui,sans-serif;background:#f8fafc;margin:0;padding:32px 16px">
<table width="100%"><tr><td align="center">
<table width="560" style="background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.08)">
<tr><td style="background:linear-gradient(135deg,#ef4444,#dc2626);padding:32px;color:#fff">
<h1 style="margin:0;font-size:24px;font-weight:800">{{ organization.name }}</h1>
<p style="margin:8px 0 0;opacity:.9;font-size:14px">ZionPay — Achat groupé</p>
</td></tr>
<tr><td style="padding:32px">
<h2 style="margin:0 0 8px;font-size:22px;color:#0f172a">Commande refusée</h2>
<p style="margin:0 0 24px;color:#64748b;font-size:14px">Votre commande n'a pas pu être validée.</p>
<div style="background:#fef2f2;border-left:4px solid #ef4444;border-radius:8px;padding:16px;margin-bottom:24px">
<p style="margin:0 0 4px;font-size:12px;color:#991b1b;text-transform:uppercase;font-weight:600">Motif</p>
<p style="margin:0;font-size:14px;color:#7f1d1d">{{ reason }}</p>
</div>
<div style="background:#f1f5f9;border-radius:12px;padding:16px;margin-bottom:24px">
<p style="margin:0 0 8px;font-size:12px;color:#64748b;text-transform:uppercase">Commande</p>
<p style="margin:0;font-size:18px;font-weight:700;color:#0f172a">{{ order_number }}</p>
</div>
<a href="{{ order_url }}" style="display:inline-block;background:#0f172a;color:#fff;padding:14px 24px;border-radius:12px;text-decoration:none;font-weight:600;font-size:14px">Voir la commande →</a>
</td></tr>
<tr><td style="padding:24px;background:#f8fafc;text-align:center;font-size:12px;color:#94a3b8">© {% now "Y" %} ZionPay</td></tr>
</table>
</td></tr></table>
</body></html>
''', "templates/emails/order_rejected.html")

write("templates/emails/order_shipping.html", '''<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="font-family:Inter,system-ui,sans-serif;background:#f8fafc;margin:0;padding:32px 16px">
<table width="100%"><tr><td align="center">
<table width="560" style="background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.08)">
<tr><td style="background:linear-gradient(135deg,#8b5cf6,#6d28d9);padding:32px;color:#fff">
<h1 style="margin:0;font-size:24px;font-weight:800">{{ organization.name }}</h1>
<p style="margin:8px 0 0;opacity:.9;font-size:14px">ZionPay — Achat groupé</p>
</td></tr>
<tr><td style="padding:32px">
<h2 style="margin:0 0 8px;font-size:22px;color:#0f172a">🚚 En cours de livraison</h2>
<p style="margin:0 0 24px;color:#64748b;font-size:14px">Votre commande est en route vers vous.</p>
<div style="background:#f1f5f9;border-radius:12px;padding:16px;margin-bottom:24px">
<p style="margin:0 0 8px;font-size:12px;color:#64748b;text-transform:uppercase">Numéro</p>
<p style="margin:0;font-size:18px;font-weight:700;color:#0f172a">{{ order_number }}</p>
</div>
<a href="{{ order_url }}" style="display:inline-block;background:#8b5cf6;color:#fff;padding:14px 24px;border-radius:12px;text-decoration:none;font-weight:600;font-size:14px">Suivre la livraison →</a>
</td></tr>
<tr><td style="padding:24px;background:#f8fafc;text-align:center;font-size:12px;color:#94a3b8">© {% now "Y" %} ZionPay</td></tr>
</table>
</td></tr></table>
</body></html>
''', "templates/emails/order_shipping.html")

# ═══════════════════════════════════════════════════════════════
# 3. Étendre email_service
# ═══════════════════════════════════════════════════════════════
p = ROOT / "apps/notifications/email_service.py"
src = p.read_text(encoding="utf-8")
if "send_order_rejected_email" not in src:
    src += '''


def send_order_rejected_email(order, reason=""):
    from django.conf import settings
    base_url = getattr(settings, "SITE_URL", "http://127.0.0.1:8000")
    return send_email(
        recipient_email=order.member.email,
        subject=f"Commande {order.order_number} refusée",
        template_name="emails/order_rejected.html",
        context={
            "organization": order.organization,
            "order_number": order.order_number,
            "reason": reason or "Non précisé",
            "order_url": f"{base_url}/orders/{order.id}/",
        },
    )


def send_order_shipping_email(order):
    from django.conf import settings
    base_url = getattr(settings, "SITE_URL", "http://127.0.0.1:8000")
    return send_email(
        recipient_email=order.member.email,
        subject=f"🚚 Commande {order.order_number} en livraison",
        template_name="emails/order_shipping.html",
        context={
            "organization": order.organization,
            "order_number": order.order_number,
            "order_url": f"{base_url}/orders/{order.id}/",
        },
    )
'''
    p.write_text(src, encoding="utf-8")
    print("  ✓ email_service étendu")

# ═══════════════════════════════════════════════════════════════
# 4. Étendre signals (SMS + nouveaux emails)
# ═══════════════════════════════════════════════════════════════
p = ROOT / "apps/notifications/signals.py"
src = p.read_text(encoding="utf-8")
if "send_order_rejected_sms" not in src:
    src += '''


# ═══════════════════════════════════════════════════════════════
# SMS sur changement de statut
# ═══════════════════════════════════════════════════════════════
@receiver(post_save, sender="orders.OrderStatusHistory")
def send_sms_on_status_change(sender, instance, created, **kwargs):
    """Envoie un SMS court quand le statut change."""
    if not created:
        return

    from .sms_service import (
        send_order_validated_sms, send_order_delivered_sms, send_order_rejected_sms,
    )

    status = instance.to_status
    order = instance.order

    try:
        if status == "VALIDEE":
            send_order_validated_sms(order)
        elif status == "LIVREE":
            send_order_delivered_sms(order)
        elif status == "REFUSEE":
            send_order_rejected_sms(order, instance.comment or "")
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════
# Emails additionnels (REFUSEE, EN_LIVRAISON)
# ═══════════════════════════════════════════════════════════════
@receiver(post_save, sender="orders.OrderStatusHistory")
def send_extra_emails(sender, instance, created, **kwargs):
    if not created:
        return
    from .email_service import send_order_rejected_email, send_order_shipping_email

    status = instance.to_status
    order = instance.order
    try:
        if status == "REFUSEE":
            send_order_rejected_email(order, instance.comment or "")
        elif status == "EN_LIVRAISON":
            send_order_shipping_email(order)
    except Exception:
        pass
'''
    p.write_text(src, encoding="utf-8")
    print("  ✓ Signals SMS + emails étendus")

# ═══════════════════════════════════════════════════════════════
# 5. Settings SMS
# ═══════════════════════════════════════════════════════════════
p = ROOT / "config/settings/base.py"
src = p.read_text(encoding="utf-8")
if "AFRICASTALKING_USERNAME" not in src:
    src += '''

# ============================================================
# SMS (Africa's Talking) — optionnel
# ============================================================
AFRICASTALKING_USERNAME = env("AFRICASTALKING_USERNAME", default="")
AFRICASTALKING_API_KEY = env("AFRICASTALKING_API_KEY", default="")
'''
    p.write_text(src, encoding="utf-8")
    print("  ✓ Settings SMS")

# ═══════════════════════════════════════════════════════════════
# 6. Dashboard Fournisseur
# ═══════════════════════════════════════════════════════════════
write("apps/catalog/supplier_views.py", '''"""Dashboard fournisseur — mes produits + commandes reçues."""
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
''', "apps/catalog/supplier_views.py")

# ═══════════════════════════════════════════════════════════════
# 7. Template dashboard fournisseur
# ═══════════════════════════════════════════════════════════════
write("templates/catalog/supplier_dashboard.html", '''{% extends "base.html" %}
{% block title %}Espace fournisseur — {{ organization.name }}{% endblock %}
{% block content %}
<div class="max-w-7xl mx-auto">

    <div class="flex items-center justify-between gap-4 mb-8">
        <div class="flex items-center gap-4">
            <div class="w-12 h-12 rounded-2xl flex items-center justify-center text-white shadow-lg"
                 style="background: linear-gradient(135deg, {{ organization.color_primary|default:'#2563eb' }}, {{ organization.color_secondary|default:'#1e40af' }});">
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/></svg>
            </div>
            <div>
                <h1 class="text-3xl font-extrabold text-slate-900">Espace fournisseur</h1>
                <p class="text-slate-500 text-sm">Gérez votre catalogue et suivez vos ventes</p>
            </div>
        </div>
    </div>

    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div class="bg-white rounded-2xl shadow-card border border-slate-100 p-5">
            <p class="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Mes produits</p>
            <p class="text-2xl font-extrabold text-slate-900">{{ products_stats.total }}</p>
            <p class="text-xs text-slate-500 mt-0.5">{{ products_stats.active }} actifs</p>
        </div>
        <div class="bg-white rounded-2xl shadow-card border border-slate-100 p-5">
            <p class="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Stock critique</p>
            <p class="text-2xl font-extrabold text-amber-600">{{ products_stats.low_stock }}</p>
            <p class="text-xs text-slate-500 mt-0.5">{{ products_stats.out_of_stock }} en rupture</p>
        </div>
        <div class="bg-white rounded-2xl shadow-card border border-slate-100 p-5">
            <p class="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Ventes</p>
            <p class="text-2xl font-extrabold text-slate-900">{{ sales_stats.total_items }}</p>
            <p class="text-xs text-slate-500 mt-0.5">{{ sales_stats.pending_count }} en attente</p>
        </div>
        <div class="bg-gradient-to-br from-emerald-500 to-emerald-700 rounded-2xl shadow-card p-5 text-white">
            <p class="text-xs font-semibold uppercase tracking-wide mb-1 opacity-90">CA généré</p>
            <p class="text-2xl font-extrabold tabular-nums">{{ sales_stats.revenue|floatformat:0 }}</p>
            <p class="text-xs opacity-90 mt-0.5">{{ organization.currency_code }}</p>
        </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <div class="bg-white rounded-2xl shadow-card border border-slate-100 p-6">
            <h2 class="font-bold text-slate-900 mb-4">Top 5 de mes produits</h2>
            {% if top_products %}
            <div class="space-y-3">
                {% for p in top_products %}
                <div class="flex items-center justify-between text-sm">
                    <span class="text-slate-700 truncate">{{ p.product__name|truncatechars:35 }}</span>
                    <span class="font-semibold text-slate-900 ml-2">{{ p.qty }} vendus</span>
                </div>
                {% endfor %}
            </div>
            {% else %}
            <p class="text-sm text-slate-500">Aucune vente pour le moment</p>
            {% endif %}
        </div>

        <div class="bg-white rounded-2xl shadow-card border border-slate-100 p-6">
            <h2 class="font-bold text-slate-900 mb-4">Alertes stock</h2>
            {% if products_stats.low_stock or products_stats.out_of_stock %}
            <div class="space-y-2 text-sm">
                {% for p in products %}
                    {% if p.stock_quantity == 0 %}
                    <div class="flex items-center gap-2 text-red-700">
                        <span class="w-2 h-2 rounded-full bg-red-500"></span>
                        <span>{{ p.name|truncatechars:40 }}</span>
                        <span class="ml-auto font-semibold">Rupture</span>
                    </div>
                    {% elif p.stock_quantity <= 10 %}
                    <div class="flex items-center gap-2 text-amber-700">
                        <span class="w-2 h-2 rounded-full bg-amber-500"></span>
                        <span>{{ p.name|truncatechars:40 }}</span>
                        <span class="ml-auto font-semibold">{{ p.stock_quantity }} restants</span>
                    </div>
                    {% endif %}
                {% endfor %}
            </div>
            {% else %}
            <p class="text-sm text-emerald-600">✓ Tous vos stocks sont au-dessus du seuil</p>
            {% endif %}
        </div>
    </div>

    <div class="bg-white rounded-2xl shadow-card border border-slate-100 overflow-hidden">
        <div class="p-6 border-b border-slate-100">
            <h2 class="font-bold text-slate-900">Commandes contenant mes produits</h2>
            <p class="text-xs text-slate-500 mt-0.5">{{ recent_items|length }} dernières lignes</p>
        </div>

        {% if recent_items %}
        <div class="overflow-x-auto">
            <table class="w-full text-sm">
                <thead class="bg-slate-50">
                    <tr>
                        <th class="p-3 text-left font-semibold text-slate-600">Commande</th>
                        <th class="p-3 text-left font-semibold text-slate-600">Produit</th>
                        <th class="p-3 text-center font-semibold text-slate-600">Qté</th>
                        <th class="p-3 text-right font-semibold text-slate-600">Montant</th>
                        <th class="p-3 text-left font-semibold text-slate-600">Statut</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-slate-100">
                    {% for item in recent_items %}
                    <tr>
                        <td class="p-3">
                            <a href="{% url 'order_detail' item.order.id %}" class="font-medium text-slate-900 hover:text-brand-600">
                                {{ item.order.order_number }}
                            </a>
                        </td>
                        <td class="p-3 text-slate-700">{{ item.product.name|truncatechars:30 }}</td>
                        <td class="p-3 text-center">{{ item.quantity }}</td>
                        <td class="p-3 text-right font-semibold">{% widthratio item.unit_price 1 item.quantity %} {{ item.order.currency_code }}</td>
                        <td class="p-3">
                            <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold
                                {% if item.order.status == 'LIVREE' %}bg-emerald-100 text-emerald-800
                                {% elif item.order.status == 'REFUSEE' %}bg-red-100 text-red-800
                                {% elif item.order.status == 'VALIDEE' %}bg-blue-100 text-blue-800
                                {% else %}bg-amber-100 text-amber-800{% endif %}">
                                {{ item.order.get_status_display }}
                            </span>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        {% else %}
        <div class="p-12 text-center">
            <p class="text-slate-500">Aucune commande pour le moment</p>
        </div>
        {% endif %}
    </div>
</div>
{% endblock %}
''', "templates/catalog/supplier_dashboard.html")

# ═══════════════════════════════════════════════════════════════
# 8. URLs
# ═══════════════════════════════════════════════════════════════
p = ROOT / "config/urls.py"
src = p.read_text(encoding="utf-8")
if "supplier_dashboard" not in src:
    src = src.replace(
        "from apps.catalog.views import catalog, product_detail",
        "from apps.catalog.views import catalog, product_detail\nfrom apps.catalog.supplier_views import supplier_dashboard",
    )
    src = src.replace(
        "    # RH Dashboard\n",
        '''    # Fournisseur
    path('supplier/', supplier_dashboard, name='supplier_dashboard'),

    # RH Dashboard
''',
    )
    p.write_text(src, encoding="utf-8")
    print("  ✓ URL /supplier/")

# ═══════════════════════════════════════════════════════════════
# 9. Navbar : lien Fournisseur
# ═══════════════════════════════════════════════════════════════
p = ROOT / "templates/components/navbar.html"
src = p.read_text(encoding="utf-8")
if "supplier_dashboard" not in src:
    src = src.replace(
        "<!-- Notifications bell -->",
        '''<!-- Fournisseur link (si applicable) -->
                    {% if user.role == 'FOURNISSEUR' or user.role == 'ADMIN' %}
                    <a href="{% url 'supplier_dashboard' %}" class="p-2 rounded-lg text-slate-700 hover:bg-slate-100 transition" title="Espace fournisseur">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/></svg>
                    </a>
                    {% endif %}

                    <!-- Notifications bell -->''', 1
    )
    p.write_text(src, encoding="utf-8")
    print("  ✓ Navbar : lien Fournisseur")

print()
print("=" * 60)
print("  PACK A3 TERMINÉ")
print("=" * 60)
