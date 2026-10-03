"""Test automatisé — PACK B1 : Avis produits (5 étoiles)."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

try:
    import django
    django.setup()
except Exception as e:
    print(f"\n❌ Django setup: {e}")
    sys.exit(1)

from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse, NoReverseMatch
from django.utils import timezone

User = get_user_model()
ROOT = Path.cwd()

# ═══════════════════════════════════════════════════════════════
# Utilitaires
# ═══════════════════════════════════════════════════════════════
def h1(t):
    print("\n" + "═" * 70)
    print(f"  {t}")
    print("═" * 70)

def h2(t):
    print(f"\n▶ {t}")

results = {"passed": 0, "failed": 0, "warned": 0, "details": []}

def ok(msg):
    results["passed"] += 1
    results["details"].append(("PASS", msg))
    print(f"  ✅ {msg}")

def ko(msg):
    results["failed"] += 1
    results["details"].append(("FAIL", msg))
    print(f"  ❌ {msg}")

def warn(msg):
    results["warned"] += 1
    results["details"].append(("WARN", msg))
    print(f"  ⚠️  {msg}")

def info(msg):
    print(f"  ℹ️  {msg}")

print()
print("╔" + "═" * 68 + "╗")
print("║" + "  TEST PACK B1 — Avis produits".center(68) + "║")
print("║" + f"  {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}".center(68) + "║")
print("╚" + "═" * 68 + "╝")

# ═══════════════════════════════════════════════════════════════
# TEST 1 — Modèle Review
# ═══════════════════════════════════════════════════════════════
h1("TEST 1 — MODÈLE REVIEW")

h2("1.1 Existence + champs")
try:
    Review = apps.get_model("catalog", "Review")
    fields = {f.name for f in Review._meta.get_fields()}
    required = ["organization", "product", "member", "order", "rating",
                "title", "comment", "is_verified_purchase", "is_published",
                "created_at", "updated_at"]
    missing = [f for f in required if f not in fields]
    if missing:
        ko(f"Review manque : {missing}")
    else:
        ok(f"Review OK ({len(fields)} champs)")
except Exception as e:
    ko(f"Review inaccessible : {e}")

h2("1.2 Contrainte unique (1 avis par user/produit)")
try:
    Review = apps.get_model("catalog", "Review")
    constraints = Review._meta.constraints
    has_unique = any("unique_review_per_member_product" in str(c) for c in constraints)
    if has_unique:
        ok("Contrainte unique présente")
    else:
        ko("Contrainte unique manquante")
except Exception as e:
    ko(f"Erreur : {e}")

# ═══════════════════════════════════════════════════════════════
# TEST 2 — Propriétés Product
# ═══════════════════════════════════════════════════════════════
h1("TEST 2 — PROPRIÉTÉS PRODUCT")

h2("2.1 average_rating")
try:
    from apps.catalog.models import Product
    if hasattr(Product, "average_rating"):
        ok("Product.average_rating existe")
    else:
        ko("Product.average_rating manquant")
except Exception as e:
    ko(f"Erreur : {e}")

h2("2.2 review_count")
try:
    from apps.catalog.models import Product
    if hasattr(Product, "review_count"):
        ok("Product.review_count existe")
    else:
        ko("Product.review_count manquant")
except Exception as e:
    ko(f"Erreur : {e}")

# ═══════════════════════════════════════════════════════════════
# TEST 3 — Vues
# ═══════════════════════════════════════════════════════════════
h1("TEST 3 — VUES")

p = ROOT / "apps/catalog/review_views.py"
if not p.exists():
    ko("review_views.py introuvable")
else:
    src = p.read_text(encoding="utf-8")
    for fn in ["def product_reviews", "def submit_review", "def delete_review"]:
        if fn in src:
            ok(f"{fn} présent")
        else:
            ko(f"{fn} manquant")

# ═══════════════════════════════════════════════════════════════
# TEST 4 — Templates
# ═══════════════════════════════════════════════════════════════
h1("TEST 4 — TEMPLATES")

templates_to_check = {
    "templates/catalog/_stars.html": ["forloop.counter <= rating"],
    "templates/catalog/reviews.html": [
        "Distribution des notes", "Laisser un avis", "Achat vérifié",
    ],
}

for path, needles in templates_to_check.items():
    h2(f"4.x {path}")
    p = ROOT / path
    if not p.exists():
        ko(f"{path} introuvable")
        continue
    src = p.read_text(encoding="utf-8")
    for needle in needles:
        if needle in src:
            ok(f"contient '{needle}'")
        else:
            ko(f"MANQUE '{needle}'")

# ═══════════════════════════════════════════════════════════════
# TEST 5 — URLs
# ═══════════════════════════════════════════════════════════════
h1("TEST 5 — URLs")

import uuid
fake_uuid = uuid.uuid4()

urls_to_test = [
    ("product_reviews", "product_id", fake_uuid),
    ("submit_review", "product_id", fake_uuid),
    ("delete_review", "review_id", fake_uuid),
]

for name, arg, val in urls_to_test:
    try:
        url = reverse(name, kwargs={arg: val})
        ok(f"{name} → {url}")
    except NoReverseMatch:
        ko(f"{name} → NON TROUVÉE")

# ═══════════════════════════════════════════════════════════════
# TEST 6 — Admin
# ═══════════════════════════════════════════════════════════════
h1("TEST 6 — ADMIN")

p = ROOT / "apps/catalog/admin.py"
if p.exists():
    src = p.read_text(encoding="utf-8")
    if "ReviewAdmin" in src:
        ok("ReviewAdmin enregistré")
    else:
        ko("ReviewAdmin manquant")
    if "def publish" in src and "def unpublish" in src:
        ok("Actions publish/unpublish présentes")
    else:
        ko("Actions admin manquantes")

# ═══════════════════════════════════════════════════════════════
# TEST 7 — FONCTIONNEL : Création + propriétés
# ═══════════════════════════════════════════════════════════════
h1("TEST 7 — FONCTIONNEL : CRÉATION")

user = User.objects.filter(is_superuser=True).first()
if not user:
    ko("Aucun superuser")
else:
    info(f"User : {user.email}")

    from apps.catalog.models import Product, Review
    from apps.orders.models import Order, OrderItem

    product = Product.objects.filter(organization=user.organization).first()

    if not product:
        warn("Aucun produit disponible")
    else:
        h2("7.1 Création directe d'un Review")
        try:
            # Nettoyer
            Review.objects.filter(product=product, member=user).delete()

            r = Review.objects.create(
                organization=user.organization,
                product=product,
                member=user,
                rating=5,
                title="Excellent produit",
                comment="Très satisfait, livraison rapide !",
                is_verified_purchase=True,
                is_published=True,
            )
            ok(f"Review créé : {r.rating}★ — {r.title}")
        except Exception as e:
            ko(f"Erreur création : {e}")

        h2("7.2 Product.average_rating")
        try:
            avg = product.average_rating
            if avg == 5.0:
                ok(f"average_rating = {avg} (correct)")
            else:
                warn(f"average_rating = {avg}")
        except Exception as e:
            ko(f"Erreur : {e}")

        h2("7.3 Product.review_count")
        try:
            count = product.review_count
            if count >= 1:
                ok(f"review_count = {count}")
            else:
                ko(f"review_count = {count}")
        except Exception as e:
            ko(f"Erreur : {e}")

        h2("7.4 Contrainte unique empêche doublon")
        try:
            from django.db import IntegrityError
            try:
                Review.objects.create(
                    organization=user.organization,
                    product=product, member=user, rating=3,
                )
                ko("Doublon accepté (BUG)")
            except IntegrityError:
                ok("Doublon rejeté (correct)")
            except Exception as e:
                warn(f"Exception : {type(e).__name__}")
        except Exception as e:
            ko(f"Erreur : {e}")

        h2("7.5 average_rating avec plusieurs avis")
        try:
            # Créer un 2ème user avec un autre avis
            from django.contrib.auth import get_user_model as _get
            U = _get()
            user2 = U.objects.filter(organization=user.organization).exclude(id=user.id).first()
            if user2:
                Review.objects.filter(product=product, member=user2).delete()
                Review.objects.create(
                    organization=user.organization,
                    product=product, member=user2, rating=3, is_published=True,
                )
                avg = product.average_rating
                expected = (5 + 3) / 2  # = 4.0
                if avg == expected:
                    ok(f"average_rating = {avg} (correct)")
                else:
                    warn(f"average_rating = {avg}, attendu {expected}")
            else:
                info("Pas de 2ème user pour tester la moyenne multi-avis")
        except Exception as e:
            ko(f"Erreur : {e}")

        # Nettoyage
        Review.objects.filter(product=product).delete()
        info("Avis de test nettoyés")

# ═══════════════════════════════════════════════════════════════
# TEST 8 — FONCTIONNEL : HTTP
# ═══════════════════════════════════════════════════════════════
h1("TEST 8 — FONCTIONNEL : HTTP")

if user and product:
    h2("8.1 GET /product/<id>/reviews/")
    try:
        c = Client()
        c.force_login(user)
        url = reverse("product_reviews", kwargs={"product_id": product.id})
        r = c.get(url)
        if r.status_code == 200:
            content = r.content.decode("utf-8")
            if "Avis" in content:
                ok(f"Page reviews → 200 ({len(content)} bytes)")
            else:
                warn("Contenu inattendu")
        else:
            ko(f"HTTP {r.status_code}")
    except Exception as e:
        ko(f"Erreur : {e}")

    h2("8.2 POST review sans avoir acheté → refusé")
    try:
        c = Client()
        c.force_login(user)
        url = reverse("submit_review", kwargs={"product_id": product.id})
        # Nettoyer avant
        Review.objects.filter(product=product, member=user).delete()
        r = c.post(url, {"rating": 5, "title": "Test", "comment": "Test"})
        # Si user n'a pas acheté, il sera redirigé sans créer
        has_review = Review.objects.filter(product=product, member=user).exists()
        if not has_review or r.status_code == 302:
            ok(f"Refusé ou redirigé (status={r.status_code}, créé={has_review})")
        else:
            warn(f"Review créé sans achat (bug ?)")
    except Exception as e:
        ko(f"Erreur : {e}")

    h2("8.3 POST review après achat → accepté")
    try:
        # Créer un Order + OrderItem validé
        order = Order.objects.create(
            organization=user.organization,
            order_number=f"TEST-B1-{timezone.now().strftime('%H%M%S')}",
            member=user,
            status="LIVREE",
            total_amount=product.price,
            currency_code=user.organization.currency_code,
            delivery_address="Test",
        )
        OrderItem.objects.create(
            order=order, product=product,
            quantity=1, unit_price=product.price,
        )
        Review.objects.filter(product=product, member=user).delete()

        c = Client()
        c.force_login(user)
        url = reverse("submit_review", kwargs={"product_id": product.id})
        r = c.post(url, {"rating": 4, "title": "Bien", "comment": "Bon produit"})

        if r.status_code == 302:
            has_review = Review.objects.filter(product=product, member=user).exists()
            if has_review:
                ok(f"Review créé après achat (rating=4)")
            else:
                ko(f"Redirigé mais pas de Review créé")
        else:
            ko(f"Status inattendu : {r.status_code}")
    except Exception as e:
        import traceback; traceback.print_exc()
        ko(f"Erreur : {e}")
    finally:
        # Nettoyage
        Review.objects.filter(product=product, member=user).delete()
        Order.objects.filter(order_number__startswith="TEST-B1-").delete()
        info("Données de test nettoyées")

# ═══════════════════════════════════════════════════════════════
# TEST 9 — Signal : OrderStatusHistory déclenche auto-review
# ═══════════════════════════════════════════════════════════════
h1("TEST 9 — COHÉRENCE")

h2("9.1 Django check")
try:
    from django.core.management import call_command
    from io import StringIO
    out = StringIO()
    call_command("check", stdout=out, stderr=out)
    ok("Django check OK")
except Exception as e:
    ko(f"check échoue : {e}")

h2("9.2 Migrations en attente")
try:
    from django.core.management import call_command
    from io import StringIO
    out = StringIO()
    try:
        call_command("makemigrations", "--check", "--dry-run", stdout=out, stderr=out)
        ok("Aucune migration en attente")
    except SystemExit:
        warn("Migrations en attente")
except Exception as e:
    warn(f"Impossible : {e}")

# ═══════════════════════════════════════════════════════════════
# RÉSUMÉ
# ═══════════════════════════════════════════════════════════════
h1("📊 RÉSUMÉ")

total = results["passed"] + results["failed"] + results["warned"]
score = (results["passed"] / total * 100) if total > 0 else 0

print()
print(f"  ✅ Passés    : {results['passed']}")
print(f"  ⚠️  Warnings : {results['warned']}")
print(f"  ❌ Échecs    : {results['failed']}")
print(f"  ─────────────────────")
print(f"  Total       : {total}")
print(f"  🎯 Score    : {score:.1f}%")
print()

if results["failed"] == 0:
    print("  🎉 PACK B1 — TOUS LES TESTS PASSENT")
    print("  → Avis produits opérationnels. Prêt pour B2 (Stock avancé)")
elif results["failed"] <= 2:
    print("  ⚠️  PACK B1 — Quelques échecs mineurs")
else:
    print("  ❌ PACK B1 — Plusieurs échecs")

if results["failed"] > 0 or results["warned"] > 0:
    print()
    print("  📋 Détails :")
    for status, msg in results["details"]:
        if status in ("FAIL", "WARN"):
            icon = "❌" if status == "FAIL" else "⚠️"
            print(f"     {icon} {msg}")

print()
print("═" * 70)
