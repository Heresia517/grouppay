"""PACK B2 — Stock avancé : historique mouvements + alertes seuil + dashboard."""
from pathlib import Path
ROOT = Path.cwd()

def patch(path, old, new, label):
    p = ROOT / path
    if not p.exists(): print(f"  ✗ {path}"); return False
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
# 1. Modèle StockMovement
# ═══════════════════════════════════════════════════════════════
p = ROOT / "apps/catalog/models.py"
src = p.read_text(encoding="utf-8")
if "class StockMovement" not in src:
    src += '''


class StockMovement(TenantModel):
    """Historique de tous les mouvements de stock (traçabilité)."""
    TYPE_CHOICES = [
        ("IN", "Entrée"),
        ("OUT", "Sortie (commande)"),
        ("ADJUST", "Ajustement manuel"),
        ("RESTORE", "Restauration (refus)"),
        ("RETURN", "Retour client"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="stock_movements")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="movements")
    movement_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    quantity = models.IntegerField(help_text="Positif = entrée, négatif = sortie")
    stock_before = models.PositiveIntegerField()
    stock_after = models.PositiveIntegerField()
    reason = models.CharField(max_length=200, blank=True)
    order = models.ForeignKey(
        "orders.Order", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="stock_movements",
    )
    actor = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="stock_movements",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["product", "-created_at"]),
            models.Index(fields=["organization", "-created_at"]),
        ]

    def __str__(self):
        sign = "+" if self.quantity > 0 else ""
        return f"{self.product.name} : {sign}{self.quantity} ({self.movement_type})"


class StockAlert(TenantModel):
    """Alerte seuil stock critique (créée une fois par franchissement)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="stock_alerts")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="alerts")
    stock_at_alert = models.PositiveIntegerField()
    reorder_level = models.PositiveIntegerField()
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"ALERTE {self.product.name} ({self.stock_at_alert}/{self.reorder_level})"
'''
    p.write_text(src, encoding="utf-8")
    print("  ✓ StockMovement + StockAlert")

# ═══════════════════════════════════════════════════════════════
# 2. Admin
# ═══════════════════════════════════════════════════════════════
p = ROOT / "apps/catalog/admin.py"
src = p.read_text(encoding="utf-8")
if "StockMovementAdmin" not in src:
    src += '''


from .models import StockMovement, StockAlert


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("created_at", "product", "movement_type", "quantity",
                    "stock_before", "stock_after", "actor")
    list_filter = ("movement_type", "organization")
    search_fields = ("product__name", "reason")
    date_hierarchy = "created_at"
    readonly_fields = [f.name for f in StockMovement._meta.fields]

    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False


@admin.register(StockAlert)
class StockAlertAdmin(admin.ModelAdmin):
    list_display = ("created_at", "product", "stock_at_alert", "reorder_level", "is_resolved")
    list_filter = ("is_resolved", "organization")
    actions = ["resolve_alerts"]

    def resolve_alerts(self, request, queryset):
        from django.utils import timezone
        queryset.update(is_resolved=True, resolved_at=timezone.now())
    resolve_alerts.short_description = "Marquer comme résolues"
'''
    p.write_text(src, encoding="utf-8")
    print("  ✓ Admin StockMovement + StockAlert")

# ═══════════════════════════════════════════════════════════════
# 3. Mettre à jour services.py pour créer les mouvements
# ═══════════════════════════════════════════════════════════════
p = ROOT / "apps/catalog/services.py"
src = p.read_text(encoding="utf-8")

# Enrichir decrement_stock
old_dec = '''    locked.stock_quantity = F("stock_quantity") - quantity
    locked.save(update_fields=["stock_quantity"])
    locked.refresh_from_db(fields=["stock_quantity"])
    return True'''

new_dec = '''    stock_before = locked.stock_quantity
    locked.stock_quantity = F("stock_quantity") - quantity
    locked.save(update_fields=["stock_quantity"])
    locked.refresh_from_db(fields=["stock_quantity"])

    # Historique mouvement
    from .models import StockMovement, StockAlert
    StockMovement.objects.create(
        organization=locked.organization,
        product=locked,
        movement_type="OUT",
        quantity=-quantity,
        stock_before=stock_before,
        stock_after=locked.stock_quantity,
        reason="Sortie commande",
    )

    # Créer une alerte si franchissement du seuil
    if stock_before > locked.reorder_level >= locked.stock_quantity:
        StockAlert.objects.create(
            organization=locked.organization,
            product=locked,
            stock_at_alert=locked.stock_quantity,
            reorder_level=locked.reorder_level,
        )

    return True'''

if old_dec in src:
    src = src.replace(old_dec, new_dec, 1)
    print("  ✓ decrement_stock enrichi (mouvement + alerte)")

# Enrichir increment_stock
old_inc = '''    locked.stock_quantity = F("stock_quantity") + quantity
    locked.save(update_fields=["stock_quantity"])
    return True'''

new_inc = '''    stock_before = locked.stock_quantity
    locked.stock_quantity = F("stock_quantity") + quantity
    locked.save(update_fields=["stock_quantity"])
    locked.refresh_from_db(fields=["stock_quantity"])

    from .models import StockMovement, StockAlert
    StockMovement.objects.create(
        organization=locked.organization,
        product=locked,
        movement_type="RESTORE",
        quantity=quantity,
        stock_before=stock_before,
        stock_after=locked.stock_quantity,
        reason="Restauration stock",
    )

    # Résoudre les alertes actives si on remonte au-dessus du seuil
    if stock_before <= locked.reorder_level < locked.stock_quantity:
        from django.utils import timezone
        StockAlert.objects.filter(
            product=locked, is_resolved=False,
        ).update(is_resolved=True, resolved_at=timezone.now())

    return True'''

if old_inc in src:
    src = src.replace(old_inc, new_inc, 1)
    print("  ✓ increment_stock enrichi (mouvement + résolution alerte)")

p.write_text(src, encoding="utf-8")

# ═══════════════════════════════════════════════════════════════
# 4. Vues stock
# ═══════════════════════════════════════════════════════════════
write("apps/catalog/stock_views.py", '''"""Vues stock avancé — historique + alertes + ajustement."""
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
    """Historique complet d'un produit."""
    _require_manager(request.user)
    product = get_object_or_404(Product, id=product_id, organization=request.user.organization)
    movements = product.movements.select_related("actor", "order")[:100]

    return render(request, "catalog/stock_history.html", {
        "product": product,
        "movements": movements,
        "total_in": product.movements.filter(quantity__gt=0).aggregate(s=Sum("quantity"))["s"] or 0,
        "total_out": abs(product.movements.filter(quantity__lt=0).aggregate(s=Sum("quantity"))["s"] or 0),
    })


@login_required
@require_POST
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
''', "apps/catalog/stock_views.py")

# ═══════════════════════════════════════════════════════════════
# 5. URLs
# ═══════════════════════════════════════════════════════════════
p = ROOT / "config/urls.py"
src = p.read_text(encoding="utf-8")
if "stock_dashboard" not in src:
    src = src.replace(
        "from apps.catalog.review_views import product_reviews, submit_review, delete_review",
        "from apps.catalog.review_views import product_reviews, submit_review, delete_review\nfrom apps.catalog.stock_views import (\n    stock_dashboard, product_stock_history, adjust_stock, resolve_alert,\n)",
    )
    src = src.replace(
        "    # Avis produits\n",
        '''    # Stock avancé
    path('stock/', stock_dashboard, name='stock_dashboard'),
    path('stock/product/<uuid:product_id>/', product_stock_history, name='stock_history'),
    path('stock/product/<uuid:product_id>/adjust/', adjust_stock, name='adjust_stock'),
    path('stock/alert/<uuid:alert_id>/resolve/', resolve_alert, name='resolve_alert'),

    # Avis produits
''',
    )
    p.write_text(src, encoding="utf-8")
    print("  ✓ URLs stock")

# ═══════════════════════════════════════════════════════════════
# 6. Templates
# ═══════════════════════════════════════════════════════════════
write("templates/catalog/stock_dashboard.html", '''{% extends "base.html" %}
{% block title %}Stock — {{ organization.name }}{% endblock %}
{% block content %}
<div class="max-w-7xl mx-auto">

    <div class="flex items-center gap-4 mb-8">
        <div class="w-12 h-12 rounded-2xl flex items-center justify-center text-white shadow-lg"
             style="background: linear-gradient(135deg, {{ organization.color_primary|default:'#2563eb' }}, {{ organization.color_secondary|default:'#1e40af' }});">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/></svg>
        </div>
        <div>
            <h1 class="text-3xl font-extrabold text-slate-900">Stock</h1>
            <p class="text-slate-500 text-sm">Mouvements, alertes et ajustements</p>
        </div>
    </div>

    <!-- KPIs -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div class="bg-white rounded-2xl shadow-card border border-slate-100 p-5">
            <p class="text-xs font-semibold text-slate-500 uppercase mb-1">Mouvements ({{ filters.period }}j)</p>
            <p class="text-2xl font-extrabold text-slate-900">{{ kpis.total_movements }}</p>
        </div>
        <div class="bg-amber-50 rounded-2xl border border-amber-200 p-5">
            <p class="text-xs font-semibold text-amber-700 uppercase mb-1">Stock faible</p>
            <p class="text-2xl font-extrabold text-amber-700">{{ kpis.low_stock_count }}</p>
        </div>
        <div class="bg-red-50 rounded-2xl border border-red-200 p-5">
            <p class="text-xs font-semibold text-red-700 uppercase mb-1">Rupture</p>
            <p class="text-2xl font-extrabold text-red-700">{{ kpis.out_of_stock_count }}</p>
        </div>
        <div class="bg-gradient-to-br from-brand-500 to-brand-700 rounded-2xl shadow-card p-5 text-white">
            <p class="text-xs font-semibold uppercase opacity-90 mb-1">Alertes actives</p>
            <p class="text-2xl font-extrabold">{{ kpis.active_alerts }}</p>
        </div>
    </div>

    <!-- Alertes -->
    {% if alerts %}
    <div class="bg-white rounded-2xl shadow-card border border-slate-100 overflow-hidden mb-6">
        <div class="p-5 border-b border-slate-100 bg-amber-50">
            <h2 class="font-bold text-amber-900">⚠️ Alertes stock actives ({{ alerts|length }})</h2>
        </div>
        <div class="divide-y divide-slate-100">
            {% for a in alerts %}
            <div class="p-4 flex items-center justify-between gap-3">
                <div>
                    <p class="font-medium text-slate-900">{{ a.product.name }}</p>
                    <p class="text-xs text-slate-500">Stock : {{ a.stock_at_alert }} / Seuil : {{ a.reorder_level }}</p>
                </div>
                <form method="post" action="{% url 'resolve_alert' a.id %}">
                    {% csrf_token %}
                    <button class="px-3 py-1.5 rounded-lg bg-emerald-100 text-emerald-700 text-xs font-semibold hover:bg-emerald-200">
                        Résoudre
                    </button>
                </form>
            </div>
            {% endfor %}
        </div>
    </div>
    {% endif %}

    <!-- Filtres -->
    <div class="bg-white rounded-2xl shadow-card border border-slate-100 p-5 mb-6">
        <form method="get" class="flex flex-wrap items-end gap-3">
            <div>
                <label class="block text-xs font-semibold text-slate-500 uppercase mb-1">Produit</label>
                <select name="product" class="rounded-lg border border-slate-200 px-3 py-2 text-sm">
                    <option value="">Tous</option>
                    {% for p in products %}
                    <option value="{{ p.id }}" {% if filters.product == p.id|stringformat:"s" %}selected{% endif %}>{{ p.name|truncatechars:40 }}</option>
                    {% endfor %}
                </select>
            </div>
            <div>
                <label class="block text-xs font-semibold text-slate-500 uppercase mb-1">Type</label>
                <select name="type" class="rounded-lg border border-slate-200 px-3 py-2 text-sm">
                    <option value="">Tous</option>
                    {% for val, label in movement_types %}
                    <option value="{{ val }}" {% if filters.type == val %}selected{% endif %}>{{ label }}</option>
                    {% endfor %}
                </select>
            </div>
            <div>
                <label class="block text-xs font-semibold text-slate-500 uppercase mb-1">Période</label>
                <select name="period" class="rounded-lg border border-slate-200 px-3 py-2 text-sm">
                    <option value="7" {% if filters.period == 7 %}selected{% endif %}>7 jours</option>
                    <option value="30" {% if filters.period == 30 %}selected{% endif %}>30 jours</option>
                    <option value="90" {% if filters.period == 90 %}selected{% endif %}>90 jours</option>
                </select>
            </div>
            <button class="px-4 py-2 rounded-lg bg-brand-600 text-white text-sm font-semibold hover:bg-brand-700">Filtrer</button>
            <a href="{% url 'stock_dashboard' %}" class="px-4 py-2 rounded-lg bg-slate-100 text-slate-700 text-sm font-semibold">Reset</a>
        </form>
    </div>

    <!-- Mouvements -->
    <div class="bg-white rounded-2xl shadow-card border border-slate-100 overflow-hidden">
        <div class="p-5 border-b border-slate-100">
            <h2 class="font-bold text-slate-900">Derniers mouvements</h2>
        </div>
        {% if movements %}
        <div class="overflow-x-auto">
            <table class="w-full text-sm">
                <thead class="bg-slate-50">
                    <tr>
                        <th class="p-3 text-left font-semibold text-slate-600">Date</th>
                        <th class="p-3 text-left font-semibold text-slate-600">Produit</th>
                        <th class="p-3 text-left font-semibold text-slate-600">Type</th>
                        <th class="p-3 text-right font-semibold text-slate-600">Qté</th>
                        <th class="p-3 text-right font-semibold text-slate-600">Avant → Après</th>
                        <th class="p-3 text-left font-semibold text-slate-600">Motif</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-slate-100">
                    {% for m in movements %}
                    <tr>
                        <td class="p-3 text-xs text-slate-500">{{ m.created_at|date:"d/m H:i" }}</td>
                        <td class="p-3 font-medium">{{ m.product.name|truncatechars:30 }}</td>
                        <td class="p-3">
                            <span class="inline-block px-2 py-0.5 rounded-full text-xs font-semibold
                                {% if m.movement_type == 'IN' %}bg-emerald-100 text-emerald-800
                                {% elif m.movement_type == 'OUT' %}bg-red-100 text-red-800
                                {% elif m.movement_type == 'RESTORE' %}bg-blue-100 text-blue-800
                                {% else %}bg-slate-100 text-slate-800{% endif %}">
                                {{ m.get_movement_type_display }}
                            </span>
                        </td>
                        <td class="p-3 text-right font-bold {% if m.quantity > 0 %}text-emerald-600{% else %}text-red-600{% endif %}">
                            {% if m.quantity > 0 %}+{% endif %}{{ m.quantity }}
                        </td>
                        <td class="p-3 text-right text-xs tabular-nums">{{ m.stock_before }} → {{ m.stock_after }}</td>
                        <td class="p-3 text-xs text-slate-500">{{ m.reason|truncatechars:40 }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        {% else %}
        <div class="p-12 text-center">
            <p class="text-slate-500">Aucun mouvement sur cette période</p>
        </div>
        {% endif %}
    </div>
</div>
{% endblock %}
''', "templates/catalog/stock_dashboard.html")

# ═══════════════════════════════════════════════════════════════
# 7. Navbar : lien Stock
# ═══════════════════════════════════════════════════════════════
p = ROOT / "templates/components/navbar.html"
src = p.read_text(encoding="utf-8")
if "url 'stock_dashboard'" not in src:
    src = src.replace(
        "<!-- Notifications bell -->",
        '''<!-- Stock link (RH/Fournisseur) -->
                    {% if user.role == 'ADMIN' or user.role == 'GESTIONNAIRE' or user.role == 'FOURNISSEUR' %}
                    <a href="{% url 'stock_dashboard' %}" class="p-2 rounded-lg text-slate-700 hover:bg-slate-100 transition" title="Stock">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/></svg>
                    </a>
                    {% endif %}

                    <!-- Notifications bell -->''', 1
    )
    p.write_text(src, encoding="utf-8")
    print("  ✓ Navbar : lien Stock")

print()
print("=" * 60)
print("  PACK B2 TERMINÉ")
print("=" * 60)
