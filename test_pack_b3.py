"""Test automatisé — PACK B3 : Multi-fournisseurs."""
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

try:
    import django
    django.setup()
except Exception as e:
    print(f"Django error: {e}")
    sys.exit(1)

from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse, NoReverseMatch
from django.utils import timezone

User = get_user_model()
ROOT = Path.cwd()

def h1(t):
    print("\n" + "=" * 70)
    print("  " + t)
    print("=" * 70)

def h2(t):
    print("\n> " + t)

results = {"passed": 0, "failed": 0, "warned": 0, "details": []}

def ok(m):
    results["passed"] += 1
    results["details"].append(("PASS", m))
    print("  OK  " + m)

def ko(m):
    results["failed"] += 1
    results["details"].append(("FAIL", m))
    print("  XX  " + m)

def warn(m):
    results["warned"] += 1
    results["details"].append(("WARN", m))
    print("  !!  " + m)

print("\n" + "=" * 70)
print("  TEST PACK B3 - Multi-fournisseurs")
print("=" * 70)

# TEST 1 - Champs Product
h1("TEST 1 - CHAMPS PRODUCT")
try:
    from apps.catalog.models import Product
    fields = {f.name for f in Product._meta.get_fields()}
    for f in ["is_supplier_private", "supplier_reference"]:
        if f in fields:
            ok("Product." + f + " existe")
        else:
            ko("Product." + f + " MANQUANT")
except Exception as e:
    ko("Erreur: " + str(e))

# TEST 2 - Vues
h1("TEST 2 - VUES")
p = ROOT / "apps/catalog/supplier_product_views.py"
if p.exists():
    src = p.read_text(encoding="utf-8")
    for fn in ["def my_products", "def product_form", "def toggle_product_active",
               "def delete_product", "def suppliers_overview"]:
        if fn in src:
            ok(fn + " present")
        else:
            ko(fn + " manquant")
else:
    ko("supplier_product_views.py introuvable")

# TEST 3 - Templates
h1("TEST 3 - TEMPLATES")
for tpl, needles in {
    "templates/catalog/supplier_products.html": ["Mes produits", "Nouveau produit"],
    "templates/catalog/supplier_product_form.html": ["Nom du produit", "Creer le produit"],
    "templates/catalog/suppliers_overview.html": ["Fournisseurs", "CA genere"],
}.items():
    h2(tpl)
    p = ROOT / tpl
    if not p.exists():
        ko(tpl + " introuvable")
        continue
    src = p.read_text(encoding="utf-8")
    for n in needles:
        if n in src:
            ok("contient '" + n + "'")
        else:
            warn("manque '" + n + "'")

# TEST 4 - URLs
h1("TEST 4 - URLs")
import uuid
fake = uuid.uuid4()
for name, arg in [
    ("supplier_my_products", None),
    ("supplier_product_new", None),
    ("supplier_product_edit", "product_id"),
    ("supplier_product_toggle", "product_id"),
    ("supplier_product_delete", "product_id"),
    ("suppliers_overview", None),
]:
    try:
        url = reverse(name, kwargs={arg: fake}) if arg else reverse(name)
        ok(name + " -> " + url)
    except NoReverseMatch:
        ko(name + " -> NON TROUVEE")

# TEST 5 - FONCTIONNEL
h1("TEST 5 - FONCTIONNEL")
user = User.objects.filter(is_superuser=True).first()
if user:
    from apps.catalog.models import Product, Category
    org = user.organization

    supplier_email = "__test_b3_supplier@test.local"
    User.objects.filter(email=supplier_email).delete()
    supplier = User.objects.create_user(
        email=supplier_email, organization=org, password="test123", role="FOURNISSEUR",
    )
    ok("Fournisseur test cree: " + supplier.email)

    h2("5.1 Creer un produit")
    try:
        category = Category.objects.filter(organization=org, is_active=True).first()
        if not category:
            category = Category.objects.create(organization=org, name="Test", slug="test-b3")

        c = Client()
        c.force_login(supplier)
        r = c.post(reverse("supplier_product_new"), {
            "name": "__Test B3 Produit",
            "category": str(category.id),
            "price": "1000",
            "stock_quantity": "20",
            "is_active": "on",
        })

        p = Product.objects.filter(name="__Test B3 Produit", supplier=supplier).first()
        if p:
            ok("Produit cree: " + p.name)
        else:
            ko("Produit non cree (status=" + str(r.status_code) + ")")
    except Exception as e:
        import traceback
        traceback.print_exc()
        ko("Erreur: " + str(e))

    h2("5.2 Isolation: fournisseur voit que ses produits")
    try:
        c = Client()
        c.force_login(supplier)
        r = c.get(reverse("supplier_my_products"))
        if r.status_code == 200:
            content = r.content.decode("utf-8")
            if "__Test B3 Produit" in content:
                ok("Son produit apparait")
            other = Product.objects.filter(organization=org).exclude(supplier=supplier).first()
            if other and other.name not in content:
                ok("Ne voit pas les produits des autres")
            else:
                warn("Voit des produits d'autres fournisseurs")
    except Exception as e:
        ko("Erreur: " + str(e))

    h2("5.3 Vue RH suppliers_overview")
    try:
        c = Client()
        c.force_login(user)
        r = c.get(reverse("suppliers_overview"))
        if r.status_code == 200:
            ok("Vue RH fournisseurs -> 200 (" + str(len(r.content)) + " bytes)")
        else:
            ko("HTTP " + str(r.status_code))
    except Exception as e:
        ko("Erreur: " + str(e))

    Product.objects.filter(name__startswith="__Test B3").delete()
    User.objects.filter(email=supplier_email).delete()
    print("  info: Donnees de test nettoyees")

# TEST 6 - Coherence
h1("TEST 6 - COHERENCE")
try:
    from django.core.management import call_command
    from io import StringIO
    out = StringIO()
    call_command("check", stdout=out, stderr=out)
    ok("Django check OK")
except Exception as e:
    ko("check echoue: " + str(e))

p = ROOT / "templates/components/navbar.html"
if p.exists():
    src = p.read_text(encoding="utf-8")
    if "supplier_my_products" in src:
        ok("Lien Mes produits dans navbar")
    else:
        ko("Lien Mes produits MANQUANT")
    if "suppliers_overview" in src:
        ok("Lien Fournisseurs dans navbar")
    else:
        ko("Lien Fournisseurs MANQUANT")

# RESUME
h1("RESUME")
total = results["passed"] + results["failed"] + results["warned"]
score = (results["passed"] / total * 100) if total > 0 else 0
print("")
print("  Passes   : " + str(results["passed"]))
print("  Warnings : " + str(results["warned"]))
print("  Echecs   : " + str(results["failed"]))
print("  Score    : " + f"{score:.1f}%")
print("")
if results["failed"] == 0:
    print("  PACK B3 - TOUS LES TESTS PASSENT")
else:
    print("  Details:")
    for s, m in results["details"]:
        if s in ("FAIL", "WARN"):
            print("     " + s + ": " + m)
print("")
