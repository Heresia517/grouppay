"""Vues pour les avis produits."""
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Avg
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from .models import Product, Review
from apps.orders.models import OrderItem


def product_reviews(request, product_id):
    """Liste des avis d'un produit (page HTML ou fragment HTMX)."""
    product = get_object_or_404(Product, id=product_id)
    reviews = product.reviews.filter(is_published=True).select_related("member")

    # Distribution des notes
    distribution = {i: 0 for i in range(1, 6)}
    for r in reviews:
        distribution[r.rating] += 1

    avg = reviews.aggregate(avg=Avg("rating"))["avg"] or 0

    # Le user peut-il reviewer ?
    can_review = False
    already_reviewed = False
    if request.user.is_authenticated:
        already_reviewed = Review.objects.filter(product=product, member=request.user).exists()
        has_bought = OrderItem.objects.filter(
            order__member=request.user,
            product=product,
            order__status__in=["VALIDEE", "EN_LIVRAISON", "LIVREE"],
        ).exists()
        can_review = has_bought and not already_reviewed

    context = {
        "product": product,
        "reviews": reviews[:50],
        "average": round(avg, 1),
        "count": reviews.count(),
        "distribution": distribution,
        "can_review": can_review,
        "already_reviewed": already_reviewed,
    }
    return render(request, "catalog/reviews.html", context)


@login_required
@require_POST
def submit_review(request, product_id):
    """Soumet un avis (POST form classique)."""
    product = get_object_or_404(Product, id=product_id)

    # Vérifier qu'il n'a pas déjà reviewé
    if Review.objects.filter(product=product, member=request.user).exists():
        messages.error(request, "Vous avez déjà laissé un avis sur ce produit.")
        return redirect("product_detail", product_id=product.id)

    # Vérifier qu'il a acheté le produit
    order_item = OrderItem.objects.filter(
        order__member=request.user,
        product=product,
        order__status__in=["VALIDEE", "EN_LIVRAISON", "LIVREE"],
    ).first()

    if not order_item:
        messages.error(request, "Vous devez avoir commandé ce produit pour laisser un avis.")
        return redirect("product_detail", product_id=product.id)

    # Validation
    try:
        rating = int(request.POST.get("rating", 0))
    except (TypeError, ValueError):
        rating = 0

    if rating < 1 or rating > 5:
        messages.error(request, "Veuillez choisir une note entre 1 et 5 étoiles.")
        return redirect("product_detail", product_id=product.id)

    title = (request.POST.get("title") or "").strip()[:120]
    comment = (request.POST.get("comment") or "").strip()

    Review.objects.create(
        organization=product.organization,
        product=product,
        member=request.user,
        order=order_item.order,
        rating=rating,
        title=title,
        comment=comment,
        is_verified_purchase=True,
        is_published=True,
    )

    messages.success(request, "Merci ! Votre avis a bien été publié.")
    return redirect("product_detail", product_id=product.id)


@login_required
@require_POST
def delete_review(request, review_id):
    """Supprime son propre avis."""
    review = get_object_or_404(Review, id=review_id, member=request.user)
    product_id = review.product_id
    review.delete()
    messages.success(request, "Votre avis a été supprimé.")
    return redirect("product_detail", product_id=product_id)
