"""Test automatisé — PACK B2 : Stock avancé (mouvements + alertes)."""
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

def h1(t):
    print("\n" + "═" * 70); print(f"  {t}"); print("═" * 70)
def h2(t): print(f"\n▶ {t}")

results = {"passed": 0, "failed": 0, "warned": 0, "details": []}
def ok(msg):
    results["passed"] += 1; results["details"].append(("PASS", msg)); print(f"  ✅ {msg}")
def ko(msg):
    results["failed"] += 1; results["details"].append(("FAIL", msg)); print(f"  ❌ {msg}")
def warn(msg):
    results["warned"] += 1; results["details"].append(("WARN", msg)); print(f"  ⚠️  {msg}")
def info(msg): print(f"  ℹ️  {msg}")

print()
print("╔" + "═" * 68 + "╗")
print("║" + "  TEST PACK B2 — Stock avancé".center(68) + "║")
print("║" + f"  {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}".center(68) + "║")
print("╚" + "═" * 68 + "╝")

# ═══════════════════════════════════════════════════════════════
# TEST 1 — Modèles
# ═══════════════════════════════════════════════════════════════
h1("TEST 1 — MODÈLES")

h2("1.1 StockMovement")
try:
    SM = apps.get_model("catalog", "StockMovement")
    fields = {f.name for f in SM._meta.get_fields()}
    required = ["organization", "product", "movement_type", "quantity",
                "stock_before", "stock_after", "reason", "order", "actor", "created_at"]
    missing = [f for f in required if f not in fields]
    if missing:
        ko(f"StockMovement manque : {missing}")
    else:
        ok(f"StockMovement OK ({len(fields)} champs)")
except Exception as e:
    ko(f"StockMovement inaccessible : {e}")

h2("1.2 StockAlert")
try:
    SA = apps.get_model("catalog", "StockAlert")
    fields = {f.name for f in SA._meta.get_fields()}
    required = ["organization", "product", "stock_at_alert", "reorder_level",
                "is_resolved", "resolved_at", "created_at"]
    missing = [f for f in required if f not in fields]
    if missing:
        ko(f"StockAlert manque : {missing}")
    else:
        ok(f"StockAlert OK ({len(fields)} champs)")
except Exception as e:
    ko(f"StockAlert inaccessible : {e}")

# ═══════════════════════════════════════════════════════════════
# TEST 2 — Services enrichis
# ═══════════════════════════════════════════════════════════════
h1("TEST 2 — SERVICES")

p = ROOT / "apps/catalog/services.py"
if not p.exists():
    ko("services.py introuvable")
else:
    src = p.read_text(encoding="utf-8")
    checks = [
        ("StockMovement.objects.create", "création mouvement"),
        ("StockAlert.objects.create", "création alerte"),
        ("movement_type=\"OUT\"", "type OUT dans decrement"),
        ("movement_type=\"RESTORE\"", "type RESTORE dans increment"),
    ]
    for needle, label in checks:
        if needle in src:
            ok(f"{label} présent")
        else:
            ko(f"{label} MANQUANT")

# ═══════════════════════════════════════════════════════════════
# TEST 3 — Vues stock
# ═══════════════════════════════════════════════════════════════
h1("TEST 3 — VUES")

p = ROOT / "apps/catalog/stock_views.py"
if not p.exists():
    ko("stock_views.py introuvable")
else:
    src = p.read_text(encoding="utf-8")
    for fn in ["def stock_dashboard", "def product_stock_history",
               "def adjust_stock", "def resolve_alert"]:
        if fn in src:
            ok(f"{fn} présent")
        else:
            ko(f"{fn} manquant")

# ═══════════════════════════════════════════════════════════════
# TEST 4 — Templates
# ═══════════════════════════════════════════════════════════════
h1("TEST 4 — TEMPLATES")

templates_to_check = {
    "templates/catalog/stock_dashboard.html": [
        "Mouvements", "Alertes", "Derniers mouvements", "adjust_stock",
    ],
}

for path, needles in templates_to_check.items():
    h2(f"4.x {path}")
    p = ROOT / path
    if not p.exists():
        ko(f"{path} introuvable"); continue
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
fake = uuid.uuid4()
for name, arg in [
    ("stock_dashboard", None),
    ("stock_history", "product_id"),
    ("adjust_stock", "product_id"),
    ("resolve_alert", "alert_id"),
]:
    try:
        url = reverse(name, kwargs={arg: fake}) if arg else reverse(name)
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
    for label in ["StockMovementAdmin", "StockAlertAdmin", "resolve_alerts"]:
        if label in src:
            ok(f"{label} présent")
        else:
            ko(f"{label} manquant")

# ═══════════════════════════════════════════════════════════════
# TEST 7 — FONCTIONNEL : decrement crée mouvement + alerte
# ═══════════════════════════════════════════════════════════════
h1("TEST 7 — FONCTIONNEL")

user = User.objects.filter(is_superuser=True).first()
if not user:
    ko("Aucun superuser")
else:
    info(f"User : {user.email}")
    from apps.catalog.models import Product, StockMovement, StockAlert
    from apps.catalog.services import decrement_stock, increment_stock

    product = Product.objects.filter(organization=user.organization).first()
    if not product:
        warn("Aucun produit")
    else:
        # Nettoyage
        StockMovement.objects.filter(product=product).delete()
        StockAlert.objects.filter(product=product).delete()

        h2("7.1 decrement_stock crée mouvement")
        product.stock_quantity = 50
        product.reorder_level = 10
        product.save()

        initial_mv = StockMovement.objects.filter(product=product).count()
        decrement_stock(product, 5)
        final_mv = StockMovement.objects.filter(product=product).count()

        if final_mv == initial_mv + 1:
            ok(f"Mouvement créé (total: {final_mv})")
            m = StockMovement.objects.filter(product=product).first()
            ok(f"  → {m.movement_type} : {m.stock_before} → {m.stock_after}")
        else:
            ko(f"Mouvement non créé ({final_mv})")

        h2("7.2 Franchissement seuil → alerte")
        # On est à 45, seuil 10 → pas d'alerte
        # Faisons tomber à 8 (sous le seuil)
        product.refresh_from_db()
        if product.stock_quantity > 8:
            decrement_stock(product, product.stock_quantity - 8)

        alerts = StockAlert.objects.filter(product=product, is_resolved=False)
        if alerts.exists():
            a = alerts.first()
            ok(f"Alerte créée : stock={a.stock_at_alert} seuil={a.reorder_level}")
        else:
            ko("Aucune alerte créée lors du franchissement")

        h2("7.3 increment_stock restaure + résout alerte")
        product.refresh_from_db()
        increment_stock(product, 20)

        product.refresh_from_db()
        if product.stock_quantity == 28:
            ok(f"Stock restauré : {product.stock_quantity}")

        # Vérifier que l'alerte est résolue
        active = StockAlert.objects.filter(product=product, is_resolved=False).count()
        if active == 0:
            ok("Alerte résolue automatiquement")
        else:
            warn(f"{active} alerte(s) encore active(s)")

# ═══════════════════════════════════════════════════════════════
# TEST 8 — HTTP
# ═══════════════════════════════════════════════════════════════
h1("TEST 8 — HTTP")

if user and product:
    h2("8.1 GET /stock/")
    try:
        c = Client(); c.force_login(user)
        r = c.get(reverse("stock_dashboard"))
        if r.status_code == 200:
            content = r.content.decode("utf-8")
            if "Stock" in content and "Mouvements" in content:
                ok(f"Dashboard stock → 200 ({len(content)} bytes)")
            else:
                warn("Contenu inattendu")
        else:
            ko(f"HTTP {r.status_code}")
    except Exception as e:
        ko(f"Erreur : {e}")

    h2("8.2 GET /stock/product/<id>/")
    try:
        c = Client(); c.force_login(user)
        r = c.get(reverse("stock_history", kwargs={"product_id": product.id}))
        if r.status_code == 200:
            ok(f"Historique produit → 200")
        else:
            ko(f"HTTP {r.status_code}")
    except Exception as e:
        ko(f"Erreur : {e}")

    h2("8.3 POST adjust_stock")
    try:
        c = Client(); c.force_login(user)
        product.refresh_from_db()
        before = product.stock_quantity

        r = c.post(reverse("adjust_stock", kwargs={"product_id": product.id}), {
            "new_quantity": 100, "reason": "Test inventaire",
        })

        product.refresh_from_db()
        if r.status_code == 302 and product.stock_quantity == 100:
            ok(f"Ajustement OK : {before} → 100")
        else:
            ko(f"Ajustement échoué (status={r.status_code}, stock={product.stock_quantity})")

        # Vérifier mouvement ADJUST
        adj = StockMovement.objects.filter(product=product, movement_type="ADJUST").first()
        if adj:
            ok(f"Mouvement ADJUST créé")
        else:
            ko("Pas de mouvement ADJUST")
    except Exception as e:
        ko(f"Erreur : {e}")

    # Nettoyage
    StockMovement.objects.filter(product=product).delete()
    StockAlert.objects.filter(product=product).delete()
    info("Données de test nettoyées")

# ═══════════════════════════════════════════════════════════════
# TEST 9 — Permission
# ═══════════════════════════════════════════════════════════════
h1("TEST 9 — PERMISSION")

h2("9.1 MEMBRE bloqué")
try:
    m = User.objects.filter(role="MEMBRE").first()
    if m:
        c = Client(); c.force_login(m)
        r = c.get(reverse("stock_dashboard"))
        if r.status_code in (403, 302):
            ok(f"MEMBRE → {r.status_code} (correct)")
        else:
            warn(f"MEMBRE → {r.status_code} (attendu 403)")
    else:
        warn("Aucun MEMBRE pour tester")
except Exception as e:
    ko(f"Erreur : {e}")

# ═══════════════════════════════════════════════════════════════
# TEST 10 — Cohérence
# ═══════════════════════════════════════════════════════════════
h1("TEST 10 — COHÉRENCE")

try:
    from django.core.management import call_command
    from io import StringIO
    out = StringIO()
    call_command("check", stdout=out, stderr=out)
    ok("Django check OK")
except Exception as e:
    ko(f"check échoue : {e}")

# Navbar
p = ROOT / "templates/components/navbar.html"
if p.exists():
    src = p.read_text(encoding="utf-8")
    if "url 'stock_dashboard'" in src:
        ok("Lien Stock dans navbar")
    else:
        ko("Lien Stock MANQUANT")

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
    print("  🎉 PACK B2 — TOUS LES TESTS PASSENT")
    print("  → Prêt pour B3 (Multi-fournisseurs)")
elif results["failed"] <= 2:
    print("  ⚠️  PACK B2 — Quelques échecs mineurs")
else:
    print("  ❌ PACK B2 — Plusieurs échecs")

if results["failed"] > 0 or results["warned"] > 0:
    print()
    print("  📋 Détails :")
    for status, msg in results["details"]:
        if status in ("FAIL", "WARN"):
            icon = "❌" if status == "FAIL" else "⚠️"
            print(f"     {icon} {msg}")

print()
print("═" * 70)
