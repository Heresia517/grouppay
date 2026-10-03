"""PACK B3 — Multi-fournisseurs (catalogue privé + gestion fournisseur)."""
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
# 1. Étendre Product avec des champs fournisseur
# ═══════════════════════════════════════════════════════════════
patch(
    "apps/catalog/models.py",
    """    sku = models.CharField(max_length=50, blank=True)
    name = models.CharField(max_length=200)""",
    """    sku = models.CharField(max_length=50, blank=True)
    name = models.CharField(max_length=200)

    # Gestion fournisseur
    is_supplier_private = models.BooleanField(
        default=False,
        help_text="Produit visible uniquement par son fournisseur (brouillon)",
    )
    supplier_reference = models.CharField(
        max_length=50, blank=True,
        help_text="Référence interne du fournisseur",
    )""",
    "Product.is_supplier_private + supplier_reference"
)

# ═══════════════════════════════════════════════════════════════
# 2. Vues : gestion produits par fournisseur
# ═══════════════════════════════════════════════════════════════
write("apps/catalog/supplier_product_views.py", '''"""Gestion des produits par les fournisseurs."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from .models import Product, Category


def _require_supplier(user):
    if user.role not in ("FOURNISSEUR", "ADMIN", "GESTIONNAIRE"):
        raise PermissionDenied("Réservé aux fournisseurs")


def _is_owner(user, product):
    return product.supplier_id == user.id or user.role in ("ADMIN", "GESTIONNAIRE")


@login_required
def my_products(request):
    """Liste des produits du fournisseur connecté."""
    _require_supplier(request.user)
    org = request.user.organization

    products = Product.objects.filter(
        organization=org, supplier=request.user,
    ).select_related("category").order_by("-created_at")

    return render(request, "catalog/supplier_products.html", {
        "products": products,
    })


@login_required
def product_form(request, product_id=None):
    """Créer ou modifier un produit."""
    _require_supplier(request.user)
    org = request.user.organization

    product = None
    if product_id:
        product = get_object_or_404(Product, id=product_id, organization=org)
        if not _is_owner(request.user, product):
            raise PermissionDenied("Vous ne pouvez modifier que vos produits")

    categories = Category.objects.filter(organization=org, is_active=True)

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        category_id = request.POST.get("category")
        price = request.POST.get("price")
        stock_quantity = request.POST.get("stock_quantity") or 0
        description = (request.POST.get("description") or "").strip()
        sku = (request.POST.get("sku") or "").strip()
        supplier_reference = (request.POST.get("supplier_reference") or "").strip()
        reorder_level = request.POST.get("reorder_level") or 10
        is_private = request.POST.get("is_supplier_private") == "on"
        is_active = request.POST.get("is_active") != "off"  # coché par défaut

        errors = []
        if not name:
            errors.append("Le nom est obligatoire")
        if not category_id:
            errors.append("La catégorie est obligatoire")
        try:
            price = float(price)
            if price < 0:
                errors.append("Le prix doit être positif")
        except (TypeError, ValueError):
            errors.append("Prix invalide")
            price = 0

        try:
            stock_quantity = int(stock_quantity)
            if stock_quantity < 0:
                errors.append("Le stock doit être positif")
                stock_quantity = 0
        except (TypeError, ValueError):
            stock_quantity = 0

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, "catalog/supplier_product_form.html", {
                "product": product, "categories": categories,
            })

        category = get_object_or_404(Category, id=category_id, organization=org)

        if product:
            product.name = name
            product.category = category
            product.price = price
            product.stock_quantity = stock_quantity
            product.description = description
            product.sku = sku
            product.supplier_reference = supplier_reference
            product.reorder_level = reorder_level
            product.is_supplier_private = is_private
            product.is_active = is_active
            product.save()
            messages.success(request, f"Produit « {name} » mis à jour.")
        else:
            product = Product.objects.create(
                organization=org,
                supplier=request.user,
                category=category,
                name=name,
                price=price,
                stock_quantity=stock_quantity,
                description=description,
                sku=sku,
                supplier_reference=supplier_reference,
                reorder_level=reorder_level,
                is_supplier_private=is_private,
                is_active=is_active,
            )
            messages.success(request, f"Produit « {name} » créé.")

        return redirect("supplier_my_products")

    return render(request, "catalog/supplier_product_form.html", {
        "product": product, "categories": categories,
    })


@login_required
@require_POST
def toggle_product_active(request, product_id):
    """Activer/désactiver un produit."""
    _require_supplier(request.user)
    product = get_object_or_404(Product, id=product_id, organization=request.user.organization)
    if not _is_owner(request.user, product):
        raise PermissionDenied()

    product.is_active = not product.is_active
    product.save(update_fields=["is_active"])
    messages.success(request, f"Produit {'activé' if product.is_active else 'désactivé'}.")
    return redirect("supplier_my_products")


@login_required
@require_POST
def delete_product(request, product_id):
    """Supprimer (soft) un produit."""
    _require_supplier(request.user)
    product = get_object_or_404(Product, id=product_id, organization=request.user.organization)
    if not _is_owner(request.user, product):
        raise PermissionDenied()

    product.is_active = False
    product.is_supplier_private = True
    product.save(update_fields=["is_active", "is_supplier_private"])
    messages.success(request, "Produit désactivé.")
    return redirect("supplier_my_products")


@login_required
def suppliers_overview(request):
    """Vue RH : liste de tous les fournisseurs + performance."""
    if request.user.role not in ("ADMIN", "GESTIONNAIRE"):
        raise PermissionDenied("Réservé RH/Admin")

    from django.contrib.auth import get_user_model
    from django.db.models import Sum, Count
    from apps.orders.models import OrderItem

    User = get_user_model()
    org = request.user.organization

    suppliers = User.objects.filter(
        organization=org, role="FOURNISSEUR", is_active=True,
    )

    data = []
    for s in suppliers:
        items = OrderItem.objects.filter(
            product__supplier=s,
            order__organization=org,
            order__status__in=["VALIDEE", "EN_LIVRAISON", "LIVREE"],
        )
        stats = {
            "supplier": s,
            "products_count": Product.objects.filter(supplier=s, is_active=True).count(),
            "orders_count": items.values("order").distinct().count(),
            "items_count": items.count(),
            "revenue": sum((i.unit_price * i.quantity for i in items), start=0),
        }
        data.append(stats)

    return render(request, "catalog/suppliers_overview.html", {
        "suppliers_data": data,
    })
''', "apps/catalog/supplier_product_views.py")

# ═══════════════════════════════════════════════════════════════
# 3. URLs
# ═══════════════════════════════════════════════════════════════
p = ROOT / "config/urls.py"
src = p.read_text(encoding="utf-8")
if "supplier_my_products" not in src:
    src = src.replace(
        "from apps.catalog.stock_views import (",
        "from apps.catalog.supplier_product_views import (\n    my_products as supplier_my_products, product_form as supplier_product_form,\n    toggle_product_active, delete_product, suppliers_overview,\n)\nfrom apps.catalog.stock_views import (",
    )
    src = src.replace(
        "    # Stock avancé\n",
        '''    # Multi-fournisseurs
    path('supplier/products/', supplier_my_products, name='supplier_my_products'),
    path('supplier/products/new/', supplier_product_form, name='supplier_product_new'),
    path('supplier/products/<uuid:product_id>/edit/', supplier_product_form, name='supplier_product_edit'),
    path('supplier/products/<uuid:product_id>/toggle/', toggle_product_active, name='supplier_product_toggle'),
    path('supplier/products/<uuid:product_id>/delete/', delete_product, name='supplier_product_delete'),
    path('rh/suppliers/', suppliers_overview, name='suppliers_overview'),

    # Stock avancé
''',
    )
    p.write_text(src, encoding="utf-8")
    print("  ✓ URLs multi-fournisseurs")

# ═══════════════════════════════════════════════════════════════
# 4. Template : Liste produits fournisseur
# ═══════════════════════════════════════════════════════════════
write("templates/catalog/supplier_products.html", '''{% extends "base.html" %}
{% block title %}Mes produits — {{ organization.name }}{% endblock %}
{% block content %}
<div class="max-w-7xl mx-auto">

    <div class="flex items-center justify-between gap-4 mb-8">
        <div class="flex items-center gap-4">
            <div class="w-12 h-12 rounded-2xl flex items-center justify-center text-white shadow-lg"
                 style="background: linear-gradient(135deg, {{ organization.color_primary|default:'#2563eb' }}, {{ organization.color_secondary|default:'#1e40af' }});">
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/></svg>
            </div>
            <div>
                <h1 class="text-3xl font-extrabold text-slate-900">Mes produits</h1>
                <p class="text-slate-500 text-sm">{{ products|length }} produit{{ products|length|pluralize }}</p>
            </div>
        </div>
        <a href="{% url 'supplier_product_new' %}" class="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-brand-600 text-white text-sm font-semibold hover:bg-brand-700 shadow-sm">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
            Nouveau produit
        </a>
    </div>

    {% if products %}
    <div class="bg-white rounded-2xl shadow-card border border-slate-100 overflow-hidden">
        <div class="overflow-x-auto">
            <table class="w-full text-sm">
                <thead class="bg-slate-50">
                    <tr>
                        <th class="p-4 text-left font-semibold text-slate-600">Produit</th>
                        <th class="p-4 text-left font-semibold text-slate-600">Catégorie</th>
                        <th class="p-4 text-right font-semibold text-slate-600">Prix</th>
                        <th class="p-4 text-center font-semibold text-slate-600">Stock</th>
                        <th class="p-4 text-center font-semibold text-slate-600">Statut</th>
                        <th class="p-4 text-center font-semibold text-slate-600">Actions</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-slate-100">
                    {% for p in products %}
                    <tr class="hover:bg-slate-50/50">
                        <td class="p-4">
                            <div class="font-medium text-slate-900">{{ p.name }}</div>
                            {% if p.sku %}<div class="text-xs text-slate-400">SKU : {{ p.sku }}</div>{% endif %}
                            {% if p.supplier_reference %}<div class="text-xs text-slate-400">Réf : {{ p.supplier_reference }}</div>{% endif %}
                        </td>
                        <td class="p-4 text-slate-600">{{ p.category.name }}</td>
                        <td class="p-4 text-right font-bold text-slate-900 tabular-nums">{{ p.price|floatformat:0 }}</td>
                        <td class="p-4 text-center">
                            <span class="inline-block px-2.5 py-1 rounded-full text-xs font-bold
                                {% if p.stock_quantity == 0 %}bg-red-100 text-red-800
                                {% elif p.stock_quantity <= p.reorder_level %}bg-amber-100 text-amber-800
                                {% else %}bg-emerald-100 text-emerald-800{% endif %}">
                                {{ p.stock_quantity }}
                            </span>
                        </td>
                        <td class="p-4 text-center">
                            {% if p.is_supplier_private %}
                            <span class="inline-block px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-200 text-slate-700">Brouillon</span>
                            {% elif p.is_active %}
                            <span class="inline-block px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">Actif</span>
                            {% else %}
                            <span class="inline-block px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-200 text-slate-700">Inactif</span>
                            {% endif %}
                        </td>
                        <td class="p-4">
                            <div class="flex items-center justify-center gap-1">
                                <a href="{% url 'supplier_product_edit' p.id %}" class="p-2 rounded-lg bg-slate-50 text-slate-600 hover:bg-slate-100" title="Modifier">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
                                </a>
                                <form method="post" action="{% url 'supplier_product_toggle' p.id %}" class="inline">
                                    {% csrf_token %}
                                    <button type="submit" class="p-2 rounded-lg bg-slate-50 text-slate-600 hover:bg-slate-100" title="Activer/Désactiver">
                                        {% if p.is_active %}⏸{% else %}▶{% endif %}
                                    </button>
                                </form>
                                <a href="{% url 'stock_history' p.id %}" class="p-2 rounded-lg bg-slate-50 text-slate-600 hover:bg-slate-100" title="Stock">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/></svg>
                                </a>
                            </div>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
    {% else %}
    <div class="text-center py-20 bg-white rounded-3xl border border-slate-100 shadow-card">
        <div class="inline-flex items-center justify-center w-20 h-20 rounded-full bg-slate-100 mb-5">
            <svg class="w-10 h-10 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/></svg>
        </div>
        <h3 class="text-xl font-bold text-slate-900 mb-2">Aucun produit pour l'instant</h3>
        <p class="text-slate-500 mb-6">Créez votre premier produit pour commencer à vendre.</p>
        <a href="{% url 'supplier_product_new' %}" class="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-brand-600 text-white font-semibold hover:bg-brand-700 shadow-sm">
            Créer mon premier produit
        </a>
    </div>
    {% endif %}
</div>
{% endblock %}
''', "templates/catalog/supplier_products.html")

# ═══════════════════════════════════════════════════════════════
# 5. Template : Formulaire produit
# ═══════════════════════════════════════════════════════════════
write("templates/catalog/supplier_product_form.html", '''{% extends "base.html" %}
{% block title %}{% if product %}Modifier{% else %}Nouveau{% endif %} produit{% endblock %}
{% block content %}
<div class="max-w-3xl mx-auto">

    <div class="flex items-center gap-3 mb-6">
        <a href="{% url 'supplier_my_products' %}" class="text-sm text-slate-600 hover:text-brand-600">← Mes produits</a>
    </div>

    <h1 class="text-3xl font-extrabold text-slate-900 mb-2">
        {% if product %}Modifier le produit{% else %}Nouveau produit{% endif %}
    </h1>
    <p class="text-slate-500 text-sm mb-8">
        {% if product %}{{ product.name }}{% else %}Ajoutez un produit à votre catalogue{% endif %}
    </p>

    <form method="post" class="bg-white rounded-2xl shadow-card border border-slate-100 p-6 space-y-5">
        {% csrf_token %}

        <div>
            <label class="block text-sm font-semibold text-slate-700 mb-1.5">Nom du produit *</label>
            <input type="text" name="name" required maxlength="200" value="{{ product.name|default:'' }}"
                   class="block w-full rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-sm">
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
                <label class="block text-sm font-semibold text-slate-700 mb-1.5">Catégorie *</label>
                <select name="category" required class="block w-full rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-sm">
                    <option value="">Choisir...</option>
                    {% for c in categories %}
                    <option value="{{ c.id }}" {% if product.category_id == c.id %}selected{% endif %}>{{ c.name }}</option>
                    {% endfor %}
                </select>
            </div>
            <div>
                <label class="block text-sm font-semibold text-slate-700 mb-1.5">Prix ({{ organization.currency_code }}) *</label>
                <input type="number" name="price" step="0.01" min="0" required value="{{ product.price|default:'' }}"
                       class="block w-full rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-sm">
            </div>
        </div>

        <div>
            <label class="block text-sm font-semibold text-slate-700 mb-1.5">Description</label>
            <textarea name="description" rows="4" placeholder="Décrivez votre produit..."
                      class="block w-full rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-sm resize-none">{{ product.description|default:'' }}</textarea>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
                <label class="block text-sm font-semibold text-slate-700 mb-1.5">Stock initial</label>
                <input type="number" name="stock_quantity" min="0" value="{{ product.stock_quantity|default:0 }}"
                       class="block w-full rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-sm">
            </div>
            <div>
                <label class="block text-sm font-semibold text-slate-700 mb-1.5">Seuil d'alerte</label>
                <input type="number" name="reorder_level" min="0" value="{{ product.reorder_level|default:10 }}"
                       class="block w-full rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-sm">
            </div>
            <div>
                <label class="block text-sm font-semibold text-slate-700 mb-1.5">SKU (optionnel)</label>
                <input type="text" name="sku" maxlength="50" value="{{ product.sku|default:'' }}"
                       class="block w-full rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-sm">
            </div>
        </div>

        <div>
            <label class="block text-sm font-semibold text-slate-700 mb-1.5">Référence fournisseur</label>
            <input type="text" name="supplier_reference" maxlength="50" value="{{ product.supplier_reference|default:'' }}"
                   placeholder="Ex: REF-12345"
                   class="block w-full rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-sm">
        </div>

        <div class="flex flex-col gap-3 pt-3 border-t border-slate-100">
            <label class="flex items-center gap-3 cursor-pointer">
                <input type="checkbox" name="is_active" {% if product.is_active or not product %}checked{% endif %}
                       class="w-4 h-4 rounded border-slate-300 text-brand-600">
                <span class="text-sm font-medium text-slate-700">Produit actif (visible aux membres)</span>
            </label>
            <label class="flex items-center gap-3 cursor-pointer">
                <input type="checkbox" name="is_supplier_private" {% if product.is_supplier_private %}checked{% endif %}
                       class="w-4 h-4 rounded border-slate-300 text-brand-600">
                <span class="text-sm font-medium text-slate-700">Brouillon (visible uniquement par vous)</span>
            </label>
        </div>

        <div class="flex justify-end gap-2 pt-4">
            <a href="{% url 'supplier_my_products' %}" class="px-4 py-2.5 rounded-xl bg-slate-100 text-slate-700 text-sm font-semibold hover:bg-slate-200">Annuler</a>
            <button type="submit" class="px-6 py-2.5 rounded-xl bg-brand-600 text-white text-sm font-semibold hover:bg-brand-700 shadow-sm">
                {% if product %}Enregistrer{% else %}Créer le produit{% endif %}
            </button>
        </div>
    </form>
</div>
{% endblock %}
''', "templates/catalog/supplier_product_form.html")

# ═══════════════════════════════════════════════════════════════
# 6. Template : Vue RH fournisseurs
# ═══════════════════════════════════════════════════════════════
write("templates/catalog/suppliers_overview.html", '''{% extends "base.html" %}
{% block title %}Fournisseurs — {{ organization.name }}{% endblock %}
{% block content %}
<div class="max-w-7xl mx-auto">

    <div class="flex items-center gap-4 mb-8">
        <div class="w-12 h-12 rounded-2xl flex items-center justify-center text-white shadow-lg"
             style="background: linear-gradient(135deg, {{ organization.color_primary|default:'#2563eb' }}, {{ organization.color_secondary|default:'#1e40af' }});">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"/></svg>
        </div>
        <div>
            <h1 class="text-3xl font-extrabold text-slate-900">Fournisseurs</h1>
            <p class="text-slate-500 text-sm">{{ suppliers_data|length }} fournisseur{{ suppliers_data|length|pluralize }}</p>
        </div>
    </div>

    {% if suppliers_data %}
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {% for data in suppliers_data %}
        <div class="bg-white rounded-2xl shadow-card border border-slate-100 p-6">
            <div class="flex items-center gap-3 mb-4">
                <div class="w-12 h-12 rounded-2xl bg-gradient-to-br from-brand-400 to-brand-600 text-white flex items-center justify-center font-bold shadow-sm">
                    {{ data.supplier.email|slice:":1"|upper }}
                </div>
                <div class="min-w-0">
                    <p class="font-bold text-slate-900 truncate">{{ data.supplier.email }}</p>
                    <p class="text-xs text-slate-500">{{ data.supplier.get_role_display }}</p>
                </div>
            </div>

            <div class="grid grid-cols-3 gap-2 mb-4">
                <div class="text-center">
                    <p class="text-xl font-extrabold text-slate-900">{{ data.products_count }}</p>
                    <p class="text-[10px] text-slate-500 uppercase font-semibold">Produits</p>
                </div>
                <div class="text-center">
                    <p class="text-xl font-extrabold text-slate-900">{{ data.orders_count }}</p>
                    <p class="text-[10px] text-slate-500 uppercase font-semibold">Commandes</p>
                </div>
                <div class="text-center">
                    <p class="text-xl font-extrabold text-emerald-600">{{ data.items_count }}</p>
                    <p class="text-[10px] text-slate-500 uppercase font-semibold">Articles</p>
                </div>
            </div>

            <div class="pt-4 border-t border-slate-100">
                <p class="text-xs text-slate-500 uppercase font-semibold">CA généré</p>
                <p class="text-2xl font-extrabold text-slate-900 tabular-nums">{{ data.revenue|floatformat:0 }} <span class="text-xs font-medium text-slate-500">{{ organization.currency_code }}</span></p>
            </div>
        </div>
        {% endfor %}
    </div>
    {% else %}
    <div class="text-center py-20 bg-white rounded-3xl border border-slate-100 shadow-card">
        <h3 class="text-xl font-bold text-slate-900 mb-2">Aucun fournisseur</h3>
        <p class="text-slate-500">Importez des utilisateurs avec le rôle FOURNISSEUR pour commencer.</p>
    </div>
    {% endif %}
</div>
{% endblock %}
''', "templates/catalog/suppliers_overview.html")

# ═══════════════════════════════════════════════════════════════
# 7. Navbar : liens
# ═══════════════════════════════════════════════════════════════
p = ROOT / "templates/components/navbar.html"
src = p.read_text(encoding="utf-8")
if "supplier_my_products" not in src:
    # Dans le dropdown user
    old = '''{% if user.role == 'ADMIN' or user.role == 'GESTIONNAIRE' %}
                            <a href="{% url 'import_members' %}"'''
    new = '''{% if user.role == 'FOURNISSEUR' or user.role == 'ADMIN' or user.role == 'GESTIONNAIRE' %}
                            <a href="{% url 'supplier_my_products' %}" class="flex items-center gap-3 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/></svg>
                                Mes produits
                            </a>
                            {% endif %}
                            {% if user.role == 'ADMIN' or user.role == 'GESTIONNAIRE' %}
                            <a href="{% url 'suppliers_overview' %}" class="flex items-center gap-3 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857"/></svg>
                                Fournisseurs
                            </a>
                            <a href="{% url 'import_members' %}"'''
    if old in src:
        src = src.replace(old, new, 1)
        p.write_text(src, encoding="utf-8")
        print("  ✓ Navbar : liens Mes produits + Fournisseurs")

print()
print("=" * 60)
print("  PACK B3 TERMINÉ")
print("=" * 60)
