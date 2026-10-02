"""Priority 1 - Étape B : Coupons UI + Wishlist + Recherche avancée."""
from pathlib import Path
ROOT = Path.cwd()

def patch(path, old, new, label):
    p = ROOT / path
    if not p.exists():
        print(f"  ✗ {path} introuvable"); return False
    src = p.read_text(encoding="utf-8")
    if old not in src:
        if new[:40] in src:
            print(f"  ℹ {label} déjà patché"); return True
        print(f"  ⚠ {label} : pattern introuvable"); return False
    p.write_text(src.replace(old, new, 1), encoding="utf-8")
    print(f"  ✓ {label}"); return True

def write(path, content, label):
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    print(f"  ✓ {label}")

# ═══════════════════════════════════════════════════════════════
# 1. Cart model : coupon_code + coupon_discount
# ═══════════════════════════════════════════════════════════════
patch(
    "apps/orders/models.py",
    """    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="OPEN")
    created_at = models.DateTimeField(auto_now_add=True)""",
    """    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="OPEN")
    coupon_code = models.CharField(max_length=30, blank=True)
    coupon_discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)""",
    "Cart.coupon_code + coupon_discount"
)

# ═══════════════════════════════════════════════════════════════
# 2. Vues : wishlist + coupons
# ═══════════════════════════════════════════════════════════════
p = ROOT / "apps/orders/views.py"
src = p.read_text(encoding="utf-8")

if "def toggle_wishlist" not in src:
    src += '''


# ═══════════════════════════════════════════════════════════════
# WISHLIST
# ═══════════════════════════════════════════════════════════════
@login_required
@require_POST
def toggle_wishlist(request, product_id):
    """Ajoute/retire un produit de la wishlist. Renvoie le HTML du bouton."""
    from apps.catalog.models import Product, WishlistItem

    product = get_object_or_404(Product, id=product_id, organization=request.user.organization)
    item, created = WishlistItem.objects.get_or_create(
        user=request.user, product=product,
        defaults={"organization": request.user.organization},
    )
    if not created:
        item.delete()
        in_wishlist = False
    else:
        in_wishlist = True

    if request.headers.get("HX-Request"):
        return render(request, "catalog/_wishlist_button.html", {
            "product": product, "in_wishlist": in_wishlist,
        })
    return redirect("catalog")


@login_required
def wishlist_page(request):
    """Page dédiée : mes favoris."""
    from apps.catalog.models import WishlistItem
    items = WishlistItem.objects.filter(user=request.user).select_related("product", "product__category")
    return render(request, "accounts/wishlist.html", {"items": items})


# ═══════════════════════════════════════════════════════════════
# COUPONS
# ═══════════════════════════════════════════════════════════════
@login_required
@require_POST
def apply_coupon(request):
    """Applique un code promo au panier (HTMX → retourne page panier)."""
    from apps.catalog.models import Coupon
    from decimal import Decimal

    code = (request.POST.get("code") or "").strip().upper()
    cart = Cart.objects.filter(user=request.user, status="OPEN").first()
    if not cart:
        return redirect("view_cart")

    try:
        coupon = Coupon.objects.get(
            organization=request.user.organization,
            code=code, is_active=True,
        )
    except Coupon.DoesNotExist:
        cart.coupon_code = ""
        cart.coupon_discount = Decimal("0")
        cart.save(update_fields=["coupon_code", "coupon_discount"])
        if request.headers.get("HX-Request"):
            return _render_cart_page(request, error=f"Code promo « {code} » invalide.")
        return redirect("view_cart")

    if not coupon.is_valid:
        if request.headers.get("HX-Request"):
            return _render_cart_page(request, error=f"Code « {code} » expiré ou épuisé.")
        return redirect("view_cart")

    subtotal = sum(i.product.price * i.quantity for i in cart.items.select_related("product"))
    discount = coupon.compute_discount(subtotal)

    cart.coupon_code = coupon.code
    cart.coupon_discount = discount
    cart.save(update_fields=["coupon_code", "coupon_discount"])

    if request.headers.get("HX-Request"):
        return _render_cart_page(request, success=f"Code « {code} » appliqué : −{discount} !")
    return redirect("view_cart")


@login_required
@require_POST
def remove_coupon(request):
    """Retire le code promo du panier."""
    from decimal import Decimal
    cart = Cart.objects.filter(user=request.user, status="OPEN").first()
    if cart:
        cart.coupon_code = ""
        cart.coupon_discount = Decimal("0")
        cart.save(update_fields=["coupon_code", "coupon_discount"])

    if request.headers.get("HX-Request"):
        return _render_cart_page(request)
    return redirect("view_cart")
'''
    p.write_text(src, encoding="utf-8")
    print("  ✓ Vues wishlist + coupons ajoutées")

# ═══════════════════════════════════════════════════════════════
# 3. Améliorer _render_cart_page pour gérer error/success
# ═══════════════════════════════════════════════════════════════
patch(
    "apps/orders/views.py",
    """def _render_cart_page(request):
    \"\"\"Retourne la page panier (utilisée en HTMX pour rafraîchir le panier).\"\"\"
    cart = Cart.objects.filter(user=request.user, status="OPEN").first()
    items = list(cart.items.select_related("product").all()) if cart else []
    return render(request, "orders/cart.html", {"items": items, "cart": cart})""",
    """def _render_cart_page(request, error=None, success=None):
    \"\"\"Retourne la page panier (utilisée en HTMX pour rafraîchir le panier).\"\"\"
    cart = Cart.objects.filter(user=request.user, status="OPEN").first()
    items = list(cart.items.select_related("product").all()) if cart else []

    # Calculs
    from decimal import Decimal
    subtotal = sum((i.product.price * i.quantity for i in items), Decimal("0"))
    discount = cart.coupon_discount if cart else Decimal("0")
    total = max(subtotal - discount, Decimal("0"))

    return render(request, "orders/cart.html", {
        "items": items, "cart": cart,
        "subtotal": subtotal, "discount": discount, "total": total,
        "error": error, "success": success,
    })""",
    "_render_cart_page avec totals + messages"
)

# ═══════════════════════════════════════════════════════════════
# 4. URLs
# ═══════════════════════════════════════════════════════════════
p = ROOT / "config/urls.py"
src = p.read_text(encoding="utf-8")

if "toggle_wishlist" not in src:
    src = src.replace(
        "    view_cart, add_to_cart, remove_from_cart, update_cart_item_qty,\n    create_order_view, order_detail, my_orders,",
        "    view_cart, add_to_cart, remove_from_cart, update_cart_item_qty,\n    create_order_view, order_detail, my_orders,\n    toggle_wishlist, wishlist_page, apply_coupon, remove_coupon,",
    )
    src = src.replace(
        "    path('cart/update/<uuid:item_id>/', update_cart_item_qty, name='update_cart_item_qty'),",
        "    path('cart/update/<uuid:item_id>/', update_cart_item_qty, name='update_cart_item_qty'),\n    path('cart/apply-coupon/', apply_coupon, name='apply_coupon'),\n    path('cart/remove-coupon/', remove_coupon, name='remove_coupon'),\n\n    # Wishlist\n    path('wishlist/', wishlist_page, name='wishlist'),\n    path('wishlist/toggle/<uuid:product_id>/', toggle_wishlist, name='toggle_wishlist'),",
    )
    p.write_text(src, encoding="utf-8")
    print("  ✓ URLs wishlist + coupons")

# ═══════════════════════════════════════════════════════════════
# 5. Catalogue : recherche + filtres
# ═══════════════════════════════════════════════════════════════
p = ROOT / "apps/orders/views.py"
src = p.read_text(encoding="utf-8")

old_catalog = '''def catalog(request):
    if not request.user.is_authenticated:
        return render(request, "catalog/catalog.html", {"products": []})
    products = Product.objects.filter(
        organization=request.user.organization, is_active=True
    ).select_related("category")
    return render(request, "catalog/catalog.html", {"products": products})'''

new_catalog = '''def catalog(request):
    if not request.user.is_authenticated:
        return render(request, "catalog/catalog.html", {"products": [], "categories": []})

    from django.db.models import Q
    from apps.catalog.models import Category, WishlistItem

    qs = Product.objects.filter(
        organization=request.user.organization, is_active=True
    ).select_related("category")

    # Filtres
    q = request.GET.get("q", "").strip()
    cat_id = request.GET.get("category", "").strip()
    min_price = request.GET.get("min_price", "").strip()
    max_price = request.GET.get("max_price", "").strip()
    in_stock = request.GET.get("in_stock") == "1"
    on_promo = request.GET.get("promo") == "1"
    sort = request.GET.get("sort", "recent")

    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
    if cat_id:
        qs = qs.filter(category_id=cat_id)
    if min_price:
        try: qs = qs.filter(price__gte=float(min_price))
        except ValueError: pass
    if max_price:
        try: qs = qs.filter(price__lte=float(max_price))
        except ValueError: pass
    if in_stock:
        qs = qs.filter(stock_quantity__gt=0)
    if on_promo:
        qs = qs.filter(discount_percent__gt=0)

    sorts = {
        "recent": "-created_at",
        "price_asc": "price",
        "price_desc": "-price",
        "name": "name",
    }
    qs = qs.order_by(sorts.get(sort, "-created_at"))

    # Wishlist IDs pour afficher le cœur
    wishlist_ids = set(
        WishlistItem.objects.filter(user=request.user).values_list("product_id", flat=True)
    )

    categories = Category.objects.filter(
        organization=request.user.organization, is_active=True
    ).order_by("display_order", "name")

    return render(request, "catalog/catalog.html", {
        "products": qs,
        "categories": categories,
        "wishlist_ids": wishlist_ids,
        "filters": {
            "q": q, "category": cat_id, "min_price": min_price,
            "max_price": max_price, "in_stock": in_stock,
            "promo": on_promo, "sort": sort,
        },
    })'''

if old_catalog in src:
    src = src.replace(old_catalog, new_catalog, 1)
    p.write_text(src, encoding="utf-8")
    print("  ✓ catalog view avec filtres + wishlist")

# ═══════════════════════════════════════════════════════════════
# 6. Template : bouton wishlist (partial)
# ═══════════════════════════════════════════════════════════════
write("templates/catalog/_wishlist_button.html", '''<button type="button"
        hx-post="{% url 'toggle_wishlist' product.id %}"
        hx-target="this"
        hx-swap="outerHTML"
        class="p-2 rounded-full bg-white/90 backdrop-blur shadow-sm hover:bg-white transition {% if in_wishlist %}text-red-500{% else %}text-slate-400{% endif %}"
        title="{% if in_wishlist %}Retirer des favoris{% else %}Ajouter aux favoris{% endif %}">
    <svg class="w-5 h-5" fill="{% if in_wishlist %}currentColor{% else %}none{% endif %}" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"/>
    </svg>
</button>
''', "templates/catalog/_wishlist_button.html")

# ═══════════════════════════════════════════════════════════════
# 7. product_card : ajouter bouton wishlist
# ═══════════════════════════════════════════════════════════════
p = ROOT / "templates/components/product_card.html"
src = p.read_text(encoding="utf-8")

if "_wishlist_button.html" not in src:
    old_promo = '''        <div class="absolute top-3 left-3 flex flex-col gap-1.5">'''
    new_promo = '''        <!-- Wishlist heart -->
        <div class="absolute top-3 right-3 z-10">
            {% include "catalog/_wishlist_button.html" with product=product in_wishlist=product.id|stringformat:"s" in wishlist_ids|default:"" %}
        </div>

        <div class="absolute top-3 left-3 flex flex-col gap-1.5">'''
    if old_promo in src:
        src = src.replace(old_promo, new_promo, 1)
        p.write_text(src, encoding="utf-8")
        print("  ✓ product_card avec bouton wishlist")

print()
print("=" * 60)
print("  ÉTAPE B — PARTIE 1 TERMINÉE")
print("=" * 60)
