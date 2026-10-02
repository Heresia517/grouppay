"""Étape B — Templates : wishlist.html, catalogue filtres, panier coupons."""
from pathlib import Path
ROOT = Path.cwd()

def write(path, content, label):
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    print(f"  ✓ {label}")

# ═══════════════════════════════════════════════════════════════
# 1. Page wishlist
# ═══════════════════════════════════════════════════════════════
write("templates/accounts/wishlist.html", '''{% extends "base.html" %}
{% block title %}Mes favoris — {{ organization.name }}{% endblock %}
{% block content %}
<div class="max-w-7xl mx-auto">
    <div class="mb-8">
        <h1 class="text-3xl font-extrabold text-slate-900">Mes favoris ❤️</h1>
        <p class="text-slate-500 mt-1">Vos produits sauvegardés · {{ items|length }} produit{{ items|length|pluralize }}</p>
    </div>

    {% if items %}
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
        {% for item in items %}
            {% include "components/product_card.html" with product=item.product in_wishlist=True %}
        {% endfor %}
    </div>
    {% else %}
    <div class="text-center py-20 bg-white rounded-3xl border border-slate-100 shadow-card">
        <div class="inline-flex items-center justify-center w-24 h-24 rounded-full bg-red-50 mb-5">
            <svg class="w-12 h-12 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"/></svg>
        </div>
        <h3 class="text-xl font-bold text-slate-900 mb-2">Aucun favori</h3>
        <p class="text-slate-500 mb-6 max-w-sm mx-auto">Cliquez sur le cœur d'un produit pour le sauvegarder ici.</p>
        <a href="{% url 'catalog' %}" class="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-brand-600 text-white font-semibold hover:bg-brand-700 shadow-sm transition">Explorer le catalogue</a>
    </div>
    {% endif %}
</div>
{% endblock %}
''', "templates/accounts/wishlist.html")

# ═══════════════════════════════════════════════════════════════
# 2. Catalogue : filtres sidebar
# ═══════════════════════════════════════════════════════════════
write("templates/catalog/catalog.html", '''{% extends "base.html" %}
{% block title %}Catalogue — {{ organization.name }}{% endblock %}

{% block content %}
{% if user.is_authenticated %}

<div class="mb-6">
    <h1 class="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">Catalogue</h1>
    <p class="text-slate-500 mt-1">Trouvez ce que vous cherchez parmi {{ products|length }} produits</p>
</div>

<div class="grid grid-cols-1 lg:grid-cols-4 gap-6">

    <!-- Filtres -->
    <aside class="lg:col-span-1">
        <form method="get" class="bg-white rounded-2xl shadow-card border border-slate-100 p-5 space-y-5 sticky top-24">
            <h2 class="font-bold text-slate-900 flex items-center gap-2">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"/></svg>
                Filtres
            </h2>

            <!-- Recherche -->
            <div>
                <label class="block text-xs font-semibold text-slate-500 uppercase mb-2">Recherche</label>
                <input type="text" name="q" value="{{ filters.q }}" placeholder="Nom du produit..."
                       class="block w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none">
            </div>

            <!-- Catégorie -->
            <div>
                <label class="block text-xs font-semibold text-slate-500 uppercase mb-2">Catégorie</label>
                <select name="category" class="block w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm">
                    <option value="">Toutes</option>
                    {% for cat in categories %}
                    <option value="{{ cat.id }}" {% if filters.category == cat.id|stringformat:"s" %}selected{% endif %}>{{ cat.name }}</option>
                    {% endfor %}
                </select>
            </div>

            <!-- Prix -->
            <div>
                <label class="block text-xs font-semibold text-slate-500 uppercase mb-2">Prix ({{ organization.currency_code }})</label>
                <div class="flex gap-2">
                    <input type="number" name="min_price" value="{{ filters.min_price }}" placeholder="Min"
                           class="block w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm">
                    <input type="number" name="max_price" value="{{ filters.max_price }}" placeholder="Max"
                           class="block w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm">
                </div>
            </div>

            <!-- Cases à cocher -->
            <div class="space-y-2">
                <label class="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" name="in_stock" value="1" {% if filters.in_stock %}checked{% endif %}
                           class="rounded border-slate-300 text-brand-600 focus:ring-brand-500">
                    <span class="text-sm text-slate-700">En stock uniquement</span>
                </label>
                <label class="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" name="promo" value="1" {% if filters.promo %}checked{% endif %}
                           class="rounded border-slate-300 text-brand-600 focus:ring-brand-500">
                    <span class="text-sm text-slate-700">En promotion</span>
                </label>
            </div>

            <!-- Tri -->
            <div>
                <label class="block text-xs font-semibold text-slate-500 uppercase mb-2">Trier par</label>
                <select name="sort" class="block w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm">
                    <option value="recent" {% if filters.sort == "recent" %}selected{% endif %}>Plus récents</option>
                    <option value="price_asc" {% if filters.sort == "price_asc" %}selected{% endif %}>Prix croissant</option>
                    <option value="price_desc" {% if filters.sort == "price_desc" %}selected{% endif %}>Prix décroissant</option>
                    <option value="name" {% if filters.sort == "name" %}selected{% endif %}>Nom (A-Z)</option>
                </select>
            </div>

            <div class="flex gap-2 pt-2">
                <button type="submit" class="flex-1 px-4 py-2 rounded-lg bg-brand-600 text-white text-sm font-semibold hover:bg-brand-700">
                    Appliquer
                </button>
                <a href="{% url 'catalog' %}" class="px-4 py-2 rounded-lg bg-slate-100 text-slate-700 text-sm font-semibold hover:bg-slate-200">
                    Reset
                </a>
            </div>
        </form>
    </aside>

    <!-- Grille produits -->
    <div class="lg:col-span-3">
        {% if products %}
        <div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-5">
            {% for product in products %}
                {% include "components/product_card.html" with product=product %}
            {% endfor %}
        </div>
        {% else %}
        <div class="text-center py-20 bg-white rounded-2xl border border-slate-100">
            <div class="inline-flex items-center justify-center w-20 h-20 rounded-full bg-slate-100 mb-4">
                <svg class="w-10 h-10 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>
            </div>
            <h3 class="text-lg font-semibold text-slate-900 mb-1">Aucun produit trouvé</h3>
            <p class="text-slate-500">Essayez de modifier vos filtres</p>
            <a href="{% url 'catalog' %}" class="inline-block mt-4 px-4 py-2 rounded-lg bg-brand-600 text-white text-sm font-semibold">Voir tout</a>
        </div>
        {% endif %}
    </div>
</div>

{% else %}
<div class="max-w-md mx-auto text-center py-20">
    <h2 class="text-2xl font-bold text-slate-900 mb-2">Connexion requise</h2>
    <p class="text-slate-500 mb-6">Connectez-vous pour accéder au catalogue.</p>
    <a href="/admin/" class="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-brand-600 text-white font-semibold">Se connecter</a>
</div>
{% endif %}
{% endblock %}
''', "templates/catalog/catalog.html (refondu)")

# ═══════════════════════════════════════════════════════════════
# 3. Panier : bloc coupon + calculs
# ═══════════════════════════════════════════════════════════════
write("templates/orders/cart.html", '''{% extends "base.html" %}
{% block title %}Panier — {{ organization.name }}{% endblock %}

{% block content %}
<div class="max-w-6xl mx-auto" id="cart-root">
    <h1 class="text-3xl font-extrabold text-slate-900 mb-2">Mon panier</h1>
    <p class="text-slate-500 mb-8">Vérifiez vos articles avant de valider votre commande</p>

    {% if error %}
    <div class="p-4 rounded-xl bg-red-50 border border-red-200 text-red-900 mb-4">
        <p class="text-sm font-medium">{{ error }}</p>
    </div>
    {% endif %}
    {% if success %}
    <div class="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-900 mb-4">
        <p class="text-sm font-medium">{{ success }}</p>
    </div>
    {% endif %}

    {% if items %}
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div class="lg:col-span-2 space-y-3">
            {% for item in items %}
            <div class="bg-white rounded-2xl shadow-card border border-slate-100 p-4 flex items-center gap-4" id="cart-item-{{ item.id }}">
                <div class="w-20 h-20 rounded-xl bg-gradient-to-br from-slate-100 to-slate-200 flex-shrink-0 flex items-center justify-center overflow-hidden">
                    {% if item.product.image %}<img src="{{ item.product.image.url }}" class="w-full h-full object-cover">{% else %}
                    <svg class="w-8 h-8 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/></svg>{% endif %}
                </div>
                <div class="flex-1 min-w-0">
                    <h3 class="font-semibold text-slate-900 truncate">{{ item.product.name }}</h3>
                    <p class="text-sm text-slate-500 mt-0.5">{{ item.product.price|floatformat:0 }} {{ organization.currency_code }}</p>
                </div>
                <div class="flex items-center gap-1 bg-slate-100 rounded-xl p-1">
                    <button hx-post="{% url 'update_cart_item_qty' item.id %}" hx-vals='{"quantity": {{ item.quantity|add:"-1" }}}' hx-target="#cart-root" hx-swap="outerHTML"
                            class="w-8 h-8 rounded-lg bg-white text-slate-700 font-bold flex items-center justify-center shadow-sm" {% if item.quantity <= 1 %}disabled{% endif %}>−</button>
                    <span class="w-8 text-center font-bold text-slate-900 text-sm">{{ item.quantity }}</span>
                    <button hx-post="{% url 'update_cart_item_qty' item.id %}" hx-vals='{"quantity": {{ item.quantity|add:"1" }}}' hx-target="#cart-root" hx-swap="outerHTML"
                            class="w-8 h-8 rounded-lg bg-white text-slate-700 font-bold flex items-center justify-center shadow-sm">+</button>
                </div>
                <div class="flex flex-col items-end gap-2 min-w-[110px]">
                    <p class="font-bold text-slate-900 text-right">{% widthratio item.product.price 1 item.quantity %} {{ organization.currency_code }}</p>
                    <button hx-get="{% url 'remove_from_cart' item.id %}" hx-target="#cart-root" hx-swap="outerHTML"
                            class="text-xs text-red-600 hover:text-red-700 font-medium">Retirer</button>
                </div>
            </div>
            {% endfor %}
            <a href="{% url 'catalog' %}" class="inline-flex items-center gap-2 text-sm font-medium text-slate-600 hover:text-brand-600 transition pt-2">← Continuer mes achats</a>
        </div>

        <div class="lg:col-span-1">
            <div class="bg-white rounded-2xl shadow-card border border-slate-100 p-6 lg:sticky lg:top-24">
                <h2 class="font-bold text-slate-900 text-lg mb-4">Récapitulatif</h2>

                <!-- Bloc coupon -->
                {% if cart.coupon_code and discount > 0 %}
                <div class="mb-4 p-3 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center justify-between">
                    <div>
                        <p class="text-xs font-semibold text-emerald-700 uppercase">Code appliqué</p>
                        <p class="font-bold text-emerald-900">{{ cart.coupon_code }}</p>
                    </div>
                    <button hx-post="{% url 'remove_coupon' %}" hx-target="#cart-root" hx-swap="outerHTML"
                            class="text-xs text-emerald-700 hover:text-red-600 font-medium">Retirer</button>
                </div>
                {% else %}
                <form hx-post="{% url 'apply_coupon' %}" hx-target="#cart-root" hx-swap="outerHTML" class="mb-4">
                    {% csrf_token %}
                    <label class="block text-xs font-semibold text-slate-500 uppercase mb-2">Code promo</label>
                    <div class="flex gap-2">
                        <input type="text" name="code" placeholder="SAVE10" required
                               class="flex-1 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm uppercase tracking-wider">
                        <button type="submit" class="px-4 py-2 rounded-lg bg-slate-900 text-white text-sm font-semibold hover:bg-slate-800">OK</button>
                    </div>
                </form>
                {% endif %}

                <!-- Totaux -->
                <dl class="space-y-2 pb-4 border-b border-slate-100">
                    <div class="flex justify-between text-sm">
                        <dt class="text-slate-500">Sous-total</dt>
                        <dd class="font-medium text-slate-900">{{ subtotal|floatformat:0 }} {{ organization.currency_code }}</dd>
                    </div>
                    {% if discount > 0 %}
                    <div class="flex justify-between text-sm">
                        <dt class="text-emerald-600 font-medium">Remise</dt>
                        <dd class="font-bold text-emerald-600">−{{ discount|floatformat:0 }} {{ organization.currency_code }}</dd>
                    </div>
                    {% endif %}
                    <div class="flex justify-between text-sm">
                        <dt class="text-slate-500">Retenue salariale</dt>
                        <dd class="font-medium text-emerald-600">Automatique</dd>
                    </div>
                </dl>

                <div class="flex justify-between items-baseline py-4">
                    <span class="font-semibold text-slate-900">Total</span>
                    <span class="text-2xl font-extrabold text-slate-900">{{ total|floatformat:0 }} <span class="text-sm font-medium text-slate-500">{{ organization.currency_code }}</span></span>
                </div>

                <form method="post" action="{% url 'create_order' %}" class="space-y-4">
                    {% csrf_token %}
                    <div>
                        <label class="block text-sm font-medium text-slate-700 mb-1.5">Adresse de livraison</label>
                        <textarea name="delivery_address" required rows="3" placeholder="Ex : Secteur 15, Ouagadougou"
                                  class="block w-full rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2.5 text-sm resize-none"></textarea>
                    </div>
                    <button type="submit" class="w-full inline-flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl bg-brand-600 text-white font-semibold hover:bg-brand-700 transition">
                        Valider ma commande
                    </button>
                    <p class="text-xs text-slate-500 text-center">💡 Le montant sera déduit automatiquement de votre salaire</p>
                </form>
            </div>
        </div>
    </div>

    {% else %}
    <div class="text-center py-20 bg-white rounded-3xl border border-slate-100 shadow-card">
        <div class="inline-flex items-center justify-center w-24 h-24 rounded-full bg-slate-100 mb-5">
            <svg class="w-12 h-12 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z"/></svg>
        </div>
        <h3 class="text-xl font-bold text-slate-900 mb-2">Votre panier est vide</h3>
        <p class="text-slate-500 mb-6">Explorez notre catalogue et ajoutez vos premiers articles.</p>
        <a href="{% url 'catalog' %}" class="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-brand-600 text-white font-semibold hover:bg-brand-700 shadow-sm transition">Explorer le catalogue</a>
    </div>
    {% endif %}
</div>
{% endblock %}
''', "templates/orders/cart.html (avec coupons)")

# ═══════════════════════════════════════════════════════════════
# 4. Navbar : lien wishlist
# ═══════════════════════════════════════════════════════════════
p = ROOT / "templates/components/navbar.html"
src = p.read_text(encoding="utf-8")
if "url 'wishlist'" not in src:
    src = src.replace(
        "<!-- Notifications bell -->",
        '''<!-- Wishlist heart -->
                    <a href="{% url 'wishlist' %}" class="p-2 rounded-lg text-slate-700 hover:bg-slate-100 transition" title="Mes favoris">
                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"/></svg>
                    </a>

                    <!-- Notifications bell -->''', 1
    )
    p.write_text(src, encoding="utf-8")
    print("  ✓ Navbar : lien wishlist")

print()
print("=" * 60)
print("  ÉTAPE B — PARTIE 2 TERMINÉE")
print("=" * 60)
