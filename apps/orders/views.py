from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_http_methods
from apps.catalog.models import Product
from .models import Cart, CartItem, Order
from .services import create_order_from_cart


def get_user_organization(request):
    """Récupère l'organisation de l'utilisateur connecté, ou None."""
    if request.user.is_authenticated:
        return request.user.organization
    return None


def view_cart(request):
    """Affiche le panier de l'utilisateur."""
    if not request.user.is_authenticated:
        return redirect('/admin/login/?next=/cart/')
    
    cart, _ = Cart.objects.get_or_create(user=request.user, defaults={"status": "OPEN"})
    items = cart.items.select_related("product")
    
    total = sum(item.product.price * item.quantity for item in items)
    
    context = {
        "cart": cart,
        "items": items,
        "total": total,
        "organization": request.user.organization,
    }
    return render(request, "orders/cart.html", context)


def add_to_cart(request, product_id):
    """Ajoute un produit au panier."""
    if not request.user.is_authenticated:
        return redirect('/admin/login/?next=/')
    
    product = get_object_or_404(Product, id=product_id, organization=request.user.organization)
    cart, _ = Cart.objects.get_or_create(user=request.user, defaults={"status": "OPEN"})
    
    item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    if not created:
        item.quantity += 1
        item.save()
    
    return redirect("view_cart")


def remove_from_cart(request, item_id):
    """Supprime un produit du panier."""
    if not request.user.is_authenticated:
        return redirect('/admin/login/?next=/cart/')
    
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    item.delete()
    return redirect("view_cart")


def create_order_view(request):
    """Crée une commande à partir du panier."""
    if not request.user.is_authenticated:
        return redirect('/admin/login/?next=/cart/')
    
    if request.method == "POST":
        delivery_address = request.POST.get("delivery_address")
        cart = Cart.objects.get(user=request.user)
        
        if not cart.items.exists():
            return render(request, "orders/cart.html", {
                "cart": cart,
                "items": [],
                "error": "Votre panier est vide.",
                "organization": request.user.organization,
            })
        
        try:
            order = create_order_from_cart(request.user, delivery_address)
            cart.status = "LOCKED"
            cart.save()
            return redirect("order_detail", order_id=order.id)
        except Exception as e:
            return render(request, "orders/cart.html", {
                "cart": cart,
                "items": cart.items.all(),
                "error": str(e),
                "organization": request.user.organization,
            })
    
    return redirect("view_cart")


def order_detail(request, order_id):
    """Affiche les détails d'une commande."""
    if not request.user.is_authenticated:
        return redirect('/admin/login/?next=/')
    
    order = get_object_or_404(Order, id=order_id, member=request.user)
    context = {
        "order": order,
        "items": order.items.select_related("product"),
        "history": order.status_history.all(),
        "organization": request.user.organization,
    }
    return render(request, "orders/order_detail.html", context)


def my_orders(request):
    """Liste des commandes de l'utilisateur."""
    if not request.user.is_authenticated:
        return redirect('/admin/login/?next=/')
    
    orders = Order.objects.filter(member=request.user).order_by("-created_at")
    context = {
        "orders": orders,
        "organization": request.user.organization,
    }
    return render(request, "orders/my_orders.html", context)
