from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Category, Product


def catalog(request):
    """Page catalogue — affiche catégories et produits."""
    organization = request.user.organization if request.user.is_authenticated else None
    
    categories = Category.objects.filter(organization=organization) if organization else []
    products = Product.objects.filter(organization=organization) if organization else []
    
    context = {
        "categories": categories,
        "products": products,
        "organization": organization,
    }
    return render(request, "catalog/catalog.html", context)


def product_detail(request, product_id):
    """Détail d'un produit."""
    product = get_object_or_404(Product, id=product_id, organization=request.user.organization)
    return render(request, "catalog/product_detail.html", {"product": product})
