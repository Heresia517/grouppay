def cart_context(request):
    """Ajoute cart_count à tous les templates."""
    if not request.user.is_authenticated:
        return {"cart_count": 0}
    try:
        from .models import Cart
        cart = Cart.objects.filter(user=request.user, status="OPEN").first()
        count = cart.items.count() if cart else 0
    except Exception:
        count = 0
    return {"cart_count": count}
