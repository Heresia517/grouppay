"""PACK B1 — Avis produits (5 étoiles + commentaires)."""
from pathlib import Path
ROOT = Path.cwd()

def patch(path, old, new, label):
    p = ROOT / path
    if not p.exists():
        print(f"  ✗ {path} introuvable"); return False
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
# 1. Modèle Review
# ═══════════════════════════════════════════════════════════════
p = ROOT / "apps/catalog/models.py"
src = p.read_text(encoding="utf-8")
if "class Review" not in src:
    src += '''


class Review(TenantModel):
    """Avis produit (5 étoiles + commentaire). Un membre ne peut reviewer
    qu'un produit qu'il a commandé et reçu."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="reviews")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    member = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="reviews")
    order = models.ForeignKey(
        "orders.Order", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="product_reviews",
    )
    rating = models.PositiveSmallIntegerField(
        choices=[(i, str(i)) for i in range(1, 6)],
    )
    title = models.CharField(max_length=120, blank=True)
    comment = models.TextField(blank=True)

    is_verified_purchase = models.BooleanField(default=False)
    is_published = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["product", "member"], name="unique_review_per_member_product"),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.product.name} — {self.rating}★ by {self.member.email}"
'''
    p.write_text(src, encoding="utf-8")
    print("  ✓ Review model")

# ═══════════════════════════════════════════════════════════════
# 2. Propriétés Product : note moyenne + count
# ═══════════════════════════════════════════════════════════════
patch(
    "apps/catalog/models.py",
    '''    @property
    def is_available(self):
        return self.stock_quantity > 0 and self.is_active

    def __str__(self):
        return self.name''',
    '''    @property
    def is_available(self):
        return self.stock_quantity > 0 and self.is_active

    @property
    def average_rating(self):
        """Note moyenne (0 si aucun avis)."""
        from django.db.models import Avg
        result = self.reviews.filter(is_published=True).aggregate(avg=Avg("rating"))
        return round(result["avg"] or 0, 1)

    @property
    def review_count(self):
        """Nombre d'avis publiés."""
        return self.reviews.filter(is_published=True).count()

    def __str__(self):
        return self.name''',
    "Product.average_rating + review_count"
)

# ═══════════════════════════════════════════════════════════════
# 3. Admin
# ═══════════════════════════════════════════════════════════════
p = ROOT / "apps/catalog/admin.py"
src = p.read_text(encoding="utf-8")
if "ReviewAdmin" not in src:
    src += '''


from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "member", "rating", "is_verified_purchase", "is_published", "created_at")
    list_filter = ("rating", "is_published", "is_verified_purchase", "organization")
    search_fields = ("product__name", "member__email", "comment")
    actions = ["publish", "unpublish"]

    def publish(self, request, queryset):
        queryset.update(is_published=True)
    publish.short_description = "Publier les avis"

    def unpublish(self, request, queryset):
        queryset.update(is_published=False)
    unpublish.short_description = "Dépublier les avis"
'''
    p.write_text(src, encoding="utf-8")
    print("  ✓ Admin Review")

# ═══════════════════════════════════════════════════════════════
# 4. Vues Review
# ═══════════════════════════════════════════════════════════════
write("apps/catalog/review_views.py", '''"""Vues pour les avis produits."""
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
''', "apps/catalog/review_views.py")

# ═══════════════════════════════════════════════════════════════
# 5. URLs
# ═══════════════════════════════════════════════════════════════
p = ROOT / "config/urls.py"
src = p.read_text(encoding="utf-8")
if "submit_review" not in src:
    src = src.replace(
        "from apps.catalog.supplier_views import supplier_dashboard",
        "from apps.catalog.supplier_views import supplier_dashboard\nfrom apps.catalog.review_views import product_reviews, submit_review, delete_review",
    )
    src = src.replace(
        "    # Fournisseur\n",
        '''    # Avis produits
    path('product/<uuid:product_id>/reviews/', product_reviews, name='product_reviews'),
    path('product/<uuid:product_id>/review/', submit_review, name='submit_review'),
    path('review/<uuid:review_id>/delete/', delete_review, name='delete_review'),

    # Fournisseur
''',
    )
    p.write_text(src, encoding="utf-8")
    print("  ✓ URLs avis")

# ═══════════════════════════════════════════════════════════════
# 6. Template partial : étoiles
# ═══════════════════════════════════════════════════════════════
write("templates/catalog/_stars.html", '''{% comment %}Affiche des étoiles. Vars : rating (0-5), size (w-4 h-4 par défaut){% endcomment %}
<div class="inline-flex items-center gap-0.5">
    {% for i in "12345" %}
        {% if forloop.counter <= rating %}
            <svg class="{{ size|default:'w-4 h-4' }} text-amber-400" fill="currentColor" viewBox="0 0 20 20">
                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/>
            </svg>
        {% else %}
            <svg class="{{ size|default:'w-4 h-4' }} text-slate-300" fill="currentColor" viewBox="0 0 20 20">
                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/>
            </svg>
        {% endif %}
    {% endfor %}
</div>
''', "templates/catalog/_stars.html")

# ═══════════════════════════════════════════════════════════════
# 7. Template reviews
# ═══════════════════════════════════════════════════════════════
write("templates/catalog/reviews.html", '''{% extends "base.html" %}
{% block title %}Avis — {{ product.name }}{% endblock %}
{% block content %}
<div class="max-w-4xl mx-auto">

    <div class="flex items-center gap-3 mb-6">
        <a href="{% url 'product_detail' product.id %}" class="text-sm text-slate-600 hover:text-brand-600">← Retour au produit</a>
    </div>

    <div class="bg-white rounded-2xl shadow-card border border-slate-100 p-6 mb-6">
        <h1 class="text-2xl font-extrabold text-slate-900 mb-2">{{ product.name }}</h1>
        <div class="flex items-center gap-4 flex-wrap">
            <div class="flex items-center gap-2">
                {% include "catalog/_stars.html" with rating=average|floatformat:"0" %}
                <span class="text-2xl font-extrabold text-slate-900">{{ average }}</span>
            </div>
            <span class="text-sm text-slate-500">sur {{ count }} avis</span>
        </div>
    </div>

    <!-- Distribution -->
    {% if count > 0 %}
    <div class="bg-white rounded-2xl shadow-card border border-slate-100 p-6 mb-6">
        <h2 class="font-bold text-slate-900 mb-4">Distribution des notes</h2>
        <div class="space-y-2">
            {% for stars, n in distribution.items %}
            <div class="flex items-center gap-3">
                <div class="flex items-center gap-1 w-16">
                    <span class="text-sm font-semibold text-slate-700">{{ stars }}</span>
                    <svg class="w-4 h-4 text-amber-400" fill="currentColor" viewBox="0 0 20 20"><path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/></svg>
                </div>
                <div class="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                    <div class="h-full bg-amber-400" style="width: {% widthratio n count 100 %}%"></div>
                </div>
                <span class="text-xs text-slate-500 w-8 text-right">{{ n }}</span>
            </div>
            {% endfor %}
        </div>
    </div>
    {% endif %}

    <!-- Formulaire nouvel avis -->
    {% if can_review %}
    <div class="bg-brand-50 border border-brand-200 rounded-2xl p-6 mb-6">
        <h2 class="font-bold text-slate-900 mb-4">✍️ Laisser un avis</h2>
        <form method="post" action="{% url 'submit_review' product.id %}" class="space-y-4">
            {% csrf_token %}
            <div>
                <label class="block text-sm font-semibold text-slate-700 mb-2">Votre note *</label>
                <div class="flex gap-1" id="rating-input">
                    {% for i in "12345" %}
                    <label class="cursor-pointer">
                        <input type="radio" name="rating" value="{{ forloop.counter }}" class="sr-only peer" required>
                        <svg class="w-8 h-8 text-slate-300 peer-checked:text-amber-400 hover:text-amber-300 transition" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/>
                        </svg>
                    </label>
                    {% endfor %}
                </div>
            </div>
            <div>
                <label class="block text-sm font-semibold text-slate-700 mb-1.5">Titre (optionnel)</label>
                <input type="text" name="title" maxlength="120" placeholder="Excellent produit !"
                       class="block w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm">
            </div>
            <div>
                <label class="block text-sm font-semibold text-slate-700 mb-1.5">Commentaire (optionnel)</label>
                <textarea name="comment" rows="4" placeholder="Partagez votre expérience..."
                          class="block w-full rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm resize-none"></textarea>
            </div>
            <button type="submit" class="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-brand-600 text-white font-semibold hover:bg-brand-700 shadow-sm">
                Publier mon avis
            </button>
        </form>
    </div>
    {% elif already_reviewed %}
    <div class="bg-emerald-50 border border-emerald-200 rounded-2xl p-4 mb-6 text-sm text-emerald-800">
        ✓ Vous avez déjà laissé un avis sur ce produit. Merci !
    </div>
    {% endif %}

    <!-- Liste des avis -->
    <div class="space-y-3">
        <h2 class="font-bold text-slate-900 text-lg mb-3">Avis ({{ count }})</h2>
        {% for r in reviews %}
        <div class="bg-white rounded-2xl shadow-card border border-slate-100 p-5">
            <div class="flex items-start gap-4">
                <div class="w-10 h-10 rounded-full bg-gradient-to-br from-brand-400 to-brand-600 text-white flex items-center justify-center text-sm font-bold flex-shrink-0">
                    {{ r.member.email|slice:":1"|upper }}
                </div>
                <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2 flex-wrap mb-1">
                        <span class="font-semibold text-slate-900 text-sm">{{ r.member.email|truncatechars:25 }}</span>
                        {% if r.is_verified_purchase %}
                        <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-bold">
                            ✓ Achat vérifié
                        </span>
                        {% endif %}
                        <span class="text-xs text-slate-400">{{ r.created_at|date:"d/m/Y" }}</span>
                    </div>
                    <div class="mb-2">{% include "catalog/_stars.html" with rating=r.rating size="w-4 h-4" %}</div>
                    {% if r.title %}<p class="font-semibold text-slate-900 text-sm mb-1">{{ r.title }}</p>{% endif %}
                    {% if r.comment %}<p class="text-slate-700 text-sm">{{ r.comment }}</p>{% endif %}
                </div>
            </div>
        </div>
        {% empty %}
        <div class="text-center py-12 bg-white rounded-2xl border border-slate-100">
            <p class="text-slate-500">Aucun avis pour le moment. Soyez le premier !</p>
        </div>
        {% endfor %}
    </div>
</div>
{% endblock %}
''', "templates/catalog/reviews.html")

print()
print("=" * 60)
print("  PACK B1 TERMINÉ")
print("=" * 60)
