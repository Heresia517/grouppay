"""Test automatisé de la Commande A : Dark mode + Profile + Models."""
import os
import sys
import django
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
try:
    django.setup()
    DJANGO_OK = True
except Exception as e:
    print(f"\n❌ Django setup: {e}")
    sys.exit(1)

from django.apps import apps
from django.conf import settings
from django.db import connection
from django.test import Client
from django.contrib.auth import get_user_model

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

# ═══════════════════════════════════════════════════════════════
# Header
# ═══════════════════════════════════════════════════════════════
print()
print("╔" + "═" * 68 + "╗")
print("║" + "  TEST AUTOMATISÉ — COMMANDE A (Dark mode + Profile)".center(68) + "║")
print("║" + f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".center(68) + "║")
print("╚" + "═" * 68 + "╝")

# ═══════════════════════════════════════════════════════════════
# TEST 1 — Modèles Django
# ═══════════════════════════════════════════════════════════════
h1("TEST 1 — MODÈLES DJANGO")

h2("1.1 User.theme_preference")
try:
    field = User._meta.get_field("theme_preference")
    choices = [c[0] for c in field.choices] if field.choices else []
    if "light" in choices and "dark" in choices:
        ok(f"User.theme_preference existe ({choices})")
    else:
        warn(f"User.theme_preference existe mais choices = {choices}")
except Exception as e:
    ko(f"User.theme_preference manquant : {e}")

h2("1.2 Modèle Coupon")
try:
    Coupon = apps.get_model("catalog", "Coupon")
    fields = {f.name for f in Coupon._meta.get_fields()}
    required = ["code", "discount_type", "discount_value", "min_order_amount",
                "max_uses", "used_count", "valid_from", "valid_to", "is_active"]
    missing = [f for f in required if f not in fields]
    if missing:
        ko(f"Coupon manque : {missing}")
    else:
        ok(f"Coupon OK ({len(fields)} champs)")
    # Test property is_valid
    if hasattr(Coupon, "is_valid"):
        ok("Coupon.is_valid existe")
    else:
        ko("Coupon.is_valid manquant")
    # Test compute_discount
    if hasattr(Coupon, "compute_discount"):
        ok("Coupon.compute_discount existe")
    else:
        ko("Coupon.compute_discount manquant")
except Exception as e:
    ko(f"Coupon inaccessible : {e}")

h2("1.3 Modèle WishlistItem")
try:
    W = apps.get_model("catalog", "WishlistItem")
    fields = {f.name for f in W._meta.get_fields()}
    required = ["user", "product", "organization", "added_at"]
    missing = [f for f in required if f not in fields]
    if missing:
        ko(f"WishlistItem manque : {missing}")
    else:
        ok(f"WishlistItem OK ({len(fields)} champs)")
except Exception as e:
    ko(f"WishlistItem inaccessible : {e}")

# ═══════════════════════════════════════════════════════════════
# TEST 2 — Fichiers templates/static
# ═══════════════════════════════════════════════════════════════
h1("TEST 2 — FICHIERS TEMPLATES")

files_to_check = {
    "templates/base.html": ["darkMode:", "gp-theme", "toggleTheme", "html.dark"],
    "templates/components/navbar.html": ["toggleTheme", "url 'profile'"],
    "templates/accounts/profile.html": ["stats.total_orders", "stats.savings", "Commandes récentes"],
}

for path, needles in files_to_check.items():
    h2(f"2.x {path}")
    p = ROOT / path
    if not p.exists():
        ko(f"{path} introuvable")
        continue
    src = p.read_text(encoding="utf-8")
    for needle in needles:
        if needle in src:
            ok(f"  contient '{needle}'")
        else:
            ko(f"  MANQUE '{needle}'")

# ═══════════════════════════════════════════════════════════════
# TEST 3 — Settings
# ═══════════════════════════════════════════════════════════════
h1("TEST 3 — SETTINGS")

h2("3.1 Dark mode config")
# Vérifier dans le HTML généré (Tailwind darkMode est dans base.html, pas settings)
p = ROOT / "templates/base.html"
if p.exists() and "darkMode: 'class'" in p.read_text(encoding="utf-8"):
    ok("Tailwind darkMode: class dans base.html")
else:
    ko("darkMode: 'class' manquant dans base.html")

h2("3.2 Session engine")
if getattr(settings, "SESSION_ENGINE", "").endswith("cached_db"):
    ok(f"SESSION_ENGINE = {settings.SESSION_ENGINE}")
else:
    warn(f"SESSION_ENGINE = {getattr(settings, 'SESSION_ENGINE', 'default')}")

# ═══════════════════════════════════════════════════════════════
# TEST 4 — URLs
# ═══════════════════════════════════════════════════════════════
h1("TEST 4 — URLs")

try:
    from django.urls import reverse
    urls_to_test = [
        ("profile", None),
        ("save_theme", None),
    ]
    for name, args in urls_to_test:
        try:
            url = reverse(name, args=args)
            ok(f"{name} → {url}")
        except Exception as e:
            ko(f"{name} → {e}")
except Exception as e:
    ko(f"Impossible de résoudre les URLs : {e}")

# ═══════════════════════════════════════════════════════════════
# TEST 5 — Vues (views.py)
# ═══════════════════════════════════════════════════════════════
h1("TEST 5 — VUES")

h2("5.1 apps/accounts/views.py")
p = ROOT / "apps/accounts/views.py"
if p.exists():
    src = p.read_text(encoding="utf-8")
    for fn in ["def profile", "def save_theme"]:
        if fn in src:
            ok(f"{fn} présent")
        else:
            ko(f"{fn} manquant")
else:
    ko("apps/accounts/views.py introuvable")

# ═══════════════════════════════════════════════════════════════
# TEST 6 — Base de données (tables)
# ═══════════════════════════════════════════════════════════════
h1("TEST 6 — BASE DE DONNÉES")

h2("6.1 Colonnes de accounts_user")
try:
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA table_info(accounts_user)")
        cols = {row[1] for row in cursor.fetchall()}
    if "theme_preference" in cols:
        ok("accounts_user.theme_preference existe")
    else:
        ko("accounts_user.theme_preference MANQUANTE — relance makemigrations + migrate")
except Exception as e:
    ko(f"Erreur : {e}")

h2("6.2 Table catalog_coupon")
try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='catalog_coupon'")
        if cursor.fetchone():
            ok("Table catalog_coupon existe")
        else:
            ko("Table catalog_coupon MANQUANTE")
except Exception as e:
    ko(f"Erreur : {e}")

h2("6.3 Table catalog_wishlistitem")
try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='catalog_wishlistitem'")
        if cursor.fetchone():
            ok("Table catalog_wishlistitem existe")
        else:
            ko("Table catalog_wishlistitem MANQUANTE")
except Exception as e:
    ko(f"Erreur : {e}")

# ═══════════════════════════════════════════════════════════════
# TEST 7 — Tests fonctionnels (client HTTP)
# ═══════════════════════════════════════════════════════════════
h1("TEST 7 — TESTS FONCTIONNELS")

# Récupérer un user de test
user = User.objects.filter(is_superuser=True).first()
if not user:
    ko("Aucun superuser trouvé — impossible de tester les vues")
else:
    info(f"User de test : {user.email}")

    # 7.1 Profile page
    h2("7.1 GET /profile/")
    try:
        client = Client()
        client.force_login(user)
        resp = client.get("/profile/")
        if resp.status_code == 200:
            content = resp.content.decode("utf-8")
            if "Mon profil" in content or "profile" in content.lower():
                ok(f"/profile/ → 200 ({len(content)} bytes)")
            else:
                warn(f"/profile/ → 200 mais contenu inattendu")
        else:
            ko(f"/profile/ → {resp.status_code}")
    except Exception as e:
        ko(f"Erreur /profile/ : {e}")

    # 7.2 save_theme API
    h2("7.2 POST /api/theme/")
    try:
        client = Client()
        client.force_login(user)
        import json
        resp = client.post(
            "/api/theme/",
            data=json.dumps({"theme": "dark"}),
            content_type="application/json",
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("ok"):
                ok(f"POST /api/theme/ → 200 {data}")
                # Vérifier en DB
                user.refresh_from_db()
                if user.theme_preference == "dark":
                    ok("User.theme_preference = 'dark' en DB")
                else:
                    ko(f"User.theme_preference = '{user.theme_preference}' (attendu 'dark')")
            else:
                ko(f"Réponse inattendue : {data}")
        else:
            ko(f"POST /api/theme/ → {resp.status_code}")
    except Exception as e:
        ko(f"Erreur /api/theme/ : {e}")

    # 7.3 HTML contient la classe dark si user.theme_preference=dark
    h2("7.3 HTML contient la classe 'dark' si user préférence=dark")
    try:
        user.refresh_from_db()
        if user.theme_preference == "dark":
            client = Client()
            client.force_login(user)
            resp = client.get("/")
            html = resp.content.decode("utf-8")
            if '<html lang="fr" class="dark"' in html or 'class="dark"' in html[:500]:
                ok("HTML contient class='dark'")
            else:
                warn("HTML ne semble pas contenir class='dark' (peut être normal au 1er chargement)")
        else:
            warn("user.theme_preference != 'dark' — test sauté")
    except Exception as e:
        ko(f"Erreur : {e}")

    # 7.4 Wishlist model (création)
    h2("7.4 Création WishlistItem")
    try:
        from apps.catalog.models import Product, WishlistItem
        product = Product.objects.filter(organization=user.organization).first()
        if product:
            item, created = WishlistItem.objects.get_or_create(
                user=user, product=product,
                defaults={"organization": user.organization},
            )
            if created:
                ok(f"WishlistItem créé pour {product.name}")
                item.delete()
                info("WishlistItem nettoyé après test")
            else:
                ok(f"WishlistItem existe déjà (idempotent)")
        else:
            warn("Aucun produit dans l'organisation — test sauté")
    except Exception as e:
        ko(f"Erreur WishlistItem : {e}")

    # 7.5 Coupon model (création + compute_discount)
    h2("7.5 Création Coupon + compute_discount")
    try:
        from apps.catalog.models import Coupon
        from decimal import Decimal

        coupon, created = Coupon.objects.get_or_create(
            organization=user.organization,
            code="TEST10",
            defaults={
                "discount_type": "percent",
                "discount_value": Decimal("10"),
                "min_order_amount": Decimal("1000"),
            },
        )
        if created:
            ok(f"Coupon TEST10 créé")
        else:
            ok(f"Coupon TEST10 existe déjà")

        # Test compute_discount
        discount = coupon.compute_discount(Decimal("50000"))
        expected = Decimal("5000.00")
        if discount == expected:
            ok(f"compute_discount(50000) = {discount} (10%)")
        else:
            ko(f"compute_discount attendu {expected}, obtenu {discount}")

        # Test sous le minimum
        discount = coupon.compute_discount(Decimal("500"))
        if discount == Decimal("0"):
            ok("compute_discount(500) = 0 (sous min_order_amount)")
        else:
            ko(f"compute_discount attendu 0, obtenu {discount}")

        # Nettoyage
        if created:
            coupon.delete()
            info("Coupon nettoyé après test")
    except Exception as e:
        ko(f"Erreur Coupon : {e}")

# ═══════════════════════════════════════════════════════════════
# TEST 8 — Cohérence globale
# ═══════════════════════════════════════════════════════════════
h1("TEST 8 — COHÉRENCE GLOBALE")

h2("8.1 Migrations en attente ?")
try:
    from django.core.management import call_command
    from io import StringIO
    out = StringIO()
    try:
        call_command("makemigrations", "--check", "--dry-run", stdout=out, stderr=out)
        ok("Aucune migration en attente")
    except SystemExit:
        warn("Migrations en attente détectées — lance: python manage.py makemigrations")
except Exception as e:
    warn(f"Impossible de vérifier : {e}")

h2("8.2 Django check")
try:
    from django.core.management import call_command
    from io import StringIO
    out = StringIO()
    call_command("check", stdout=out)
    ok("Django check : OK")
except Exception as e:
    ko(f"Django check échoue : {e}")

# ═══════════════════════════════════════════════════════════════
# RÉSUMÉ FINAL
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
    print("  🎉 COMMANDE A — TOUS LES TESTS PASSENT")
    print("  Tu peux passer à la Commande B (Coupons + Wishlist + Recherche)")
elif results["failed"] <= 2:
    print("  ⚠️  COMMANDE A — Quelques échecs mineurs")
    print("  Corrige-les puis relance ce script")
else:
    print("  ❌ COMMANDE A — Plusieurs échecs")
    print("  Relance le script de patch puis ce test")

if results["failed"] > 0 or results["warned"] > 0:
    print()
    print("  📋 Détails des problèmes :")
    for status, msg in results["details"]:
        if status in ("FAIL", "WARN"):
            icon = "❌" if status == "FAIL" else "⚠️"
            print(f"     {icon} {msg}")

print()
print("═" * 70)
