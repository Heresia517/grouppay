from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

from apps.catalog.models import Product
from .models import Cart, CartItem, Order, OrderStatusHistory


# ─── Helpers ────────────────────────────────────────────────────

def _get_open_cart(user):
    """Retourne le cart OPEN. Si le cart existe en LOCKED (après commande),
    on le réactive en le vidant — l'utilisateur peut recommencer."""
    cart, created = Cart.objects.get_or_create(user=user, defaults={"status": "OPEN"})
    if not created and cart.status != "OPEN":
        cart.items.all().delete()
        cart.status = "OPEN"
        cart.save(update_fields=["status"])
    return cart


def _render_cart_page(request, error=None, success=None):
    """Retourne la page panier (utilisée en HTMX pour rafraîchir le panier)."""
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
    })


def _render_cart_badge(request):
    """Retourne juste le badge (pour HTMX swap dans la navbar)."""
    cart = Cart.objects.filter(user=request.user, status="OPEN").first()
    count = cart.items.count() if cart else 0
    return render(request, "orders/cart_badge.html", {"count": count})


# ─── Catalogue ──────────────────────────────────────────────────

def catalog(request):
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
    })


def product_detail(request, product_id):
    product = get_object_or_404(
        Product, id=product_id, organization=request.user.organization
    )
    return render(request, "catalog/product_detail.html", {"product": product})


# ─── Panier ─────────────────────────────────────────────────────

@login_required
def view_cart(request):
    """Affiche le panier. Reutilise le panier existant (contrainte UNIQUE user_id)."""
    from .models import Cart
    
    # 1. On cherche le panier de l'utilisateur (peu importe son statut)
    cart = Cart.objects.filter(user=request.user).first()
    
    if cart:
        # Si le panier n'est plus "OPEN" (ex: il vient d'etre valide),
        # on le vide et on le repasse en "OPEN" pour qu'il soit reutilisable.
        if cart.status != "OPEN":
            cart.items.all().delete()
            cart.status = "OPEN"
            cart.save()
    else:
        # Si c'est le tout premier panier de l'utilisateur
        cart = Cart.objects.create(user=request.user, status="OPEN")
        
    items = cart.items.select_related("product").all()
    
    subtotal = 0
    for item in items:
        line_total = item.product.price * item.quantity
        item.line_total = line_total
        subtotal += line_total
    
    return render(request, "orders/cart.html", {
        "cart": cart,
        "items": items,
        "subtotal": subtotal,
        "total": subtotal,
    })

@login_required
@require_POST
def add_to_cart(request, product_id):
    """Ajoute un produit au panier. HTMX → retourne le badge."""
    product = get_object_or_404(
        Product, id=product_id, organization=request.user.organization
    )
    cart = _get_open_cart(request.user)

    item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    if not created:
        item.quantity += 1
        item.save(update_fields=["quantity"])

    if request.headers.get("HX-Request"):
        response = _render_cart_badge(request)
        response["HX-Trigger"] = '{"productAdded": {"name": "' + product.name + '"}}'
        return response
    return redirect("view_cart")


@login_required
def remove_from_cart(request, item_id):
    """Retire un article. HTMX → retourne la page panier mise à jour."""
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    item.delete()

    if request.headers.get("HX-Request"):
        return _render_cart_page(request)
    return redirect("view_cart")


@login_required
@require_POST
def update_cart_item_qty(request, item_id):
    """Met à jour la quantité d'un article (HTMX stepper +/-)."""
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)

    try:
        qty = int(request.POST.get("quantity", 1))
    except (TypeError, ValueError):
        qty = 1

    if qty <= 0:
        item.delete()
    else:
        # Ne pas dépasser le stock
        qty = min(qty, item.product.stock_quantity)
        item.quantity = qty
        item.save(update_fields=["quantity"])

    if request.headers.get("HX-Request"):
        return _render_cart_page(request)
    return redirect("view_cart")


# ─── Commandes ──────────────────────────────────────────────────

@login_required
def create_order_view(request):
    """Valide le panier -> cree la commande -> redirige vers le detail."""
    from django.contrib import messages
    from django.shortcuts import redirect
    from .models import Cart
    from .services import create_order_from_cart

    # 1. Recuperer le panier
    cart = Cart.objects.filter(user=request.user, status="OPEN").first()
    if not cart or not cart.items.exists():
        messages.warning(request, "Votre panier est vide.")
        return redirect("catalog")

    # 2. Recuperer l'adresse de livraison depuis le formulaire (POST)
    delivery_address = request.POST.get("delivery_address", "").strip()
    if not delivery_address:
        # Fallback : utiliser le service ou la direction du membre
        service = getattr(request.user, "service", None)
        direction = getattr(service, "direction", None) if service else None
        delivery_address = (
            f"{request.user.first_name} {request.user.last_name} - "
            f"{service.name if service else ''}, {direction.name if direction else ''}"
        ).strip(" -, ")

    # 3. Appeler le service avec la BONNE signature
    try:
        order = create_order_from_cart(
            user=request.user,
            delivery_address=delivery_address,
        )
        messages.success(
            request,
            f"Commande {order.order_number} validee avec succes !",
        )
        return redirect("order_detail", order_id=order.id)

    except Exception as e:
        messages.error(request, f"Erreur lors de la validation : {e}")
        return redirect("view_cart")

@login_required
def my_orders(request):
    """Liste des commandes filtrée selon le périmètre de l'utilisateur."""
    user = request.user
    org = user.organization

    # ─── Filtrage par périmètre ───
    if user.is_dg or user.role == "ADMIN":
        orders_qs = Order.objects.filter(organization=org)
    elif user.role == "GESTIONNAIRE":
        orders_qs = Order.objects.filter(organization=org)
    elif user.is_director:
        try:
            dir_ids = list(user.directed_directions.values_list("id", flat=True))
            orders_qs = Order.objects.filter(
                organization=org,
                member__service__direction_id__in=dir_ids,
            )
        except Exception:
            orders_qs = Order.objects.filter(organization=org, member=user)
    elif user.is_service_chief and user.service_id:
        orders_qs = Order.objects.filter(
            organization=org,
            member__service_id=user.service_id,
        )
    else:
        orders_qs = Order.objects.filter(organization=org, member=user)

    orders_qs = orders_qs.select_related("member").order_by("-created_at")

    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(orders_qs, 20)
    page = request.GET.get("page", 1)
    orders_page = paginator.get_page(page)

    return render(request, "orders/my_orders.html", {
        "orders": orders_page,
        "page_obj": orders_page,
        "is_paginated": paginator.num_pages > 1,
        "total": orders_qs.count(),
    })

@login_required
def order_detail(request, order_id):
    """Detail commande : membre voit les siennes, chef son service, RH/dir tout."""
    from django.shortcuts import get_object_or_404, render
    from django.core.exceptions import PermissionDenied

    user = request.user
    org = user.organization

    # Base : la commande doit etre dans l'organisation de l'utilisateur
    qs = Order.objects.filter(organization=org)

    # Filtrage par perimetre
    if user.is_dg or user.role == "ADMIN" or user.role == "GESTIONNAIRE":
        # Admin/RH : voient toutes les commandes de l'org
        order = get_object_or_404(qs, id=order_id)
    elif user.is_director:
        # Directeur : voit les commandes de sa direction
        try:
            dir_ids = list(user.directed_directions.values_list("id", flat=True))
            order = get_object_or_404(qs, id=order_id, member__service__direction_id__in=dir_ids)
        except Exception:
            order = get_object_or_404(qs, id=order_id, member=user)
    elif user.is_service_chief and user.service_id:
        # Chef : voit les commandes de son service
        order = get_object_or_404(qs, id=order_id, member__service_id=user.service_id)
    else:
        # Membre simple : voit uniquement SES commandes
        order = get_object_or_404(qs, id=order_id, member=user)

    return render(request, "orders/order_detail.html", {"order": order})

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
