"""Gestion des produits par les fournisseurs."""
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
