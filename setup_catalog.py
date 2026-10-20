"""Seed catalogue de démonstration GroupPay Burkina Faso."""
import os, sys
from pathlib import Path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.base")
os.environ["GROUPPAY_MODE"] = "desktop"

try:
    import django
    django.setup()
except Exception as e:
    print("Erreur Django:", e); sys.exit(1)

from decimal import Decimal
from apps.organizations.models import Organization
from apps.accounts.models import User
from apps.catalog.models import Category, Product, Coupon, ProductVariant
from django.utils import timezone
from datetime import timedelta


def get_field_names(model):
    """Retourne les noms de champs réels du modèle."""
    return {f.name for f in model._meta.get_fields() if hasattr(f, "attname")}


def safe_create(model, **kwargs):
    """Crée un objet en ignorant les champs non existants."""
    valid = get_field_names(model)
    filtered = {k: v for k, v in kwargs.items() if k in valid}
    return model.objects.create(**filtered)


def safe_get_or_create(model, lookup, **defaults):
    valid = get_field_names(model)
    filtered = {k: v for k, v in defaults.items() if k in valid}
    return model.objects.get_or_create(**lookup, defaults=filtered)


# ═══════════════════════════════════════════════════════════════
# Setup
# ═══════════════════════════════════════════════════════════════
org = Organization.objects.first()
if not org:
    print("Aucune organisation. Lance : python manage.py seed_users")
    sys.exit(1)

print(f"Organisation : {org.name}")
print()

# Fournisseurs de démo
suppliers = []
for email in ["fournisseur1@sonabel-demo.com", "fournisseur2@sonabel-demo.com"]:
    u = User.objects.filter(email=email).first()
    if u:
        suppliers.append(u)
print(f"Fournisseurs disponibles : {len(suppliers)}")
print()

# ═══════════════════════════════════════════════════════════════
# 1. CATÉGORIES
# ═══════════════════════════════════════════════════════════════
CATEGORIES = [
    ("Alimentation", "alimentation", "Riz, huile, sucre, pâtes, conserves", 1),
    ("Hygiène & Soins", "hygiene-soins", "Savon, dentifrice, détergents", 2),
    ("Électroménager", "electromenager", "Ventilateurs, fers à repasser, bouilloires", 3),
    ("Textile", "textile", "Pagnes, draps, serviettes, vêtements", 4),
    ("Papeterie", "papeterie", "Cahiers, stylos, ramettes, classeurs", 5),
    ("Électronique", "electronique", "Téléphones, radios, accessoires", 6),
    ("Mobilier", "mobilier", "Chaises, tables, lits, armoires", 7),
    ("Construction", "construction", "Ciment, peinture, quincaillerie", 8),
]

cats = {}
for name, slug, desc, order in CATEGORIES:
    c, created = safe_get_or_create(
        Category,
        {"organization": org, "slug": slug},
        name=name,
        organization=org,
        slug=slug,
        description=desc,
        is_active=True,
        display_order=order,
    )
    cats[slug] = c
    print(f"  {'[NEW]' if created else '[EXI]'} {name}")

print(f"\n=> {len(cats)} catégories\n")

# ═══════════════════════════════════════════════════════════════
# 2. PRODUITS (prix HT en FCFA)
# ═══════════════════════════════════════════════════════════════
PRODUITS = [
    # Alimentation
    ("Riz parfumé 25 kg", "alimentation", 18500, 100, "Sac de riz parfumé de 25 kg"),
    ("Huile végétale 5 L", "alimentation", 6250, 200, "Huile de cuisine 5 litres"),
    ("Sucre en poudre 1 kg", "alimentation", 700, 500, "Sucre blanc granulé"),
    ("Pâtes alimentaires 500 g", "alimentation", 450, 800, "Spaghetti / macaroni"),
    ("Lait en poudre 400 g", "alimentation", 3500, 150, "Lait en poudre instantané"),
    ("Tomate concentrée 400 g", "alimentation", 650, 600, "Boîte de concentré"),
    ("Savon de Marseille 400 g", "alimentation", 500, 1000, "Savon multi-usage"),

    # Hygiène
    ("Savon de toilette x6", "hygiene-soins", 1800, 300, "Lot de 6 savons parfumés"),
    ("Dentifrice 100 ml", "hygiene-soins", 900, 400, "Dentifrice au fluor"),
    ("Détergent lessive 5 kg", "hygiene-soins", 4500, 200, "Poudre à lessive"),
    ("Eau de javel 1 L", "hygiene-soins", 550, 500, "Javel concentrée"),
    ("Papier hygiénique x12", "hygiene-soins", 2500, 250, "Lot de 12 rouleaux"),

    # Électroménager
    ("Ventilateur sur pied", "electromenager", 22000, 30, "Ventilateur 3 vitesses"),
    ("Fer à repasser", "electromenager", 12500, 50, "Fer vapeur 1200 W"),
    ("Bouilloire électrique", "electromenager", 8500, 80, "Bouilloire 1,7 L"),
    ("Mixeur plongeant", "electromenager", 15000, 40, "Mixeur 400 W"),
    ("Réfrigérateur 150 L", "electromenager", 185000, 10, "Réfrigérateur 2 portes"),

    # Textile
    ("Pagne wax 6 yards", "textile", 8500, 200, "Pagne wax authentique"),
    ("Drap 2 places", "textile", 6500, 150, "Drap coton 220x240"),
    ("Serviette de bain", "textile", 3500, 250, "Serviette éponge 70x140"),
    ("Moustiquaire imprégnée", "textile", 4500, 400, "Moustiquaire 2 places"),

    # Papeterie
    ("Cahier 200 pages", "papeterie", 350, 1000, "Cahier grand format"),
    ("Stylo bille bleu x10", "papeterie", 500, 800, "Lot de 10 stylos"),
    ("Ramette A4 500 feuilles", "papeterie", 3500, 200, "Papier A4 80g"),
    ("Classeur à levier", "papeterie", 1200, 300, "Classeur A4 dos 7 cm"),

    # Électronique
    ("Téléphone basique", "electronique", 15000, 60, "Téléphone 2G simple"),
    ("Radio FM portative", "electronique", 8500, 80, "Radio AM/FM"),
    ("Écouteurs filaires", "electronique", 1500, 400, "Écouteurs jack 3,5 mm"),
    ("Chargeur universel", "electronique", 2500, 250, "Chargeur USB multi-embouts"),
    ("Lampe torche LED", "electronique", 2000, 300, "Lampe rechargeable"),

    # Mobilier
    ("Chaise plastique", "mobilier", 4500, 200, "Chaise monobloc"),
    ("Table pliante", "mobilier", 18000, 40, "Table 120x60 cm"),
    ("Armoire 2 portes", "mobilier", 75000, 15, "Armoire en bois"),
    ("Matelas 2 places", "mobilier", 35000, 25, "Matelas mousse 140x190"),

    # Construction
    ("Ciment 50 kg", "construction", 5500, 500, "Sac de ciment CPJ 35"),
    ("Peinture blanche 5 L", "construction", 12500, 60, "Peinture acrylique"),
    ("Fer à béton 12 mm", "construction", 4500, 300, "Barre de fer 12 m"),
    ("Clous 5 cm 1 kg", "construction", 1500, 400, "Clous acier"),
]

created_count = 0
for i, (name, cat_slug, price, stock, desc) in enumerate(PRODUITS):
    slug = name.lower().replace(" ", "-").replace("'", "").replace("(", "").replace(")", "")[:60]
    supplier = suppliers[i % len(suppliers)] if suppliers else None

    defaults = {
        "organization": org,
        "category": cats.get(cat_slug),
        "name": name,
        "slug": slug,
        "description": desc,
        "price": Decimal(str(price)),
        "unit_price": Decimal(str(price)),
        "stock": stock,
        "stock_quantity": stock,
        "is_active": True,
        "supplier": supplier,
        "created_at": timezone.now(),
    }

    p, created = safe_get_or_create(
        Product,
        {"organization": org, "slug": slug},
        **defaults
    )
    if created:
        created_count += 1

print(f"=> {created_count} nouveaux produits (total {Product.objects.count()})\n")

# ═══════════════════════════════════════════════════════════════
# 3. COUPONS
# ═══════════════════════════════════════════════════════════════
now = timezone.now()
COUPONS = [
    ("BIENVENUE10", "10% sur la 1ère commande", 10, now, now + timedelta(days=90)),
    ("RENTREE5000", "-5000 FCFA dès 50 000", 10, now, now + timedelta(days=60)),
    ("FIDELE15", "15% pour les membres fidèles", 15, now, now + timedelta(days=180)),
]

coupon_count = 0
for code, desc, pct, start, end in COUPONS:
    defaults = {
        "organization": org,
        "code": code,
        "description": desc,
        "discount_type": "percentage",
        "discount_value": Decimal(str(pct)),
        "percent": pct,
        "valid_from": start,
        "valid_until": end,
        "is_active": True,
        "max_uses": 100,
    }
    c, created = safe_get_or_create(Coupon, {"organization": org, "code": code}, **defaults)
    if created:
        coupon_count += 1

print(f"=> {coupon_count} nouveaux coupons\n")

# ═══════════════════════════════════════════════════════════════
# 4. RÉSUMÉ
# ═══════════════════════════════════════════════════════════════
print("=" * 60)
print("  CATALOGUE DE DÉMONSTRATION — PRÊT")
print("=" * 60)
print(f"  Catégories : {Category.objects.count()}")
print(f"  Produits   : {Product.objects.count()}")
print(f"  Coupons    : {Coupon.objects.count()}")
print()
print("  Voir le catalogue :")
print("    python manage.py runserver")
print("    http://127.0.0.1:8000/catalog/")
print()
print("  Admin :")
print("    http://127.0.0.1:8000/admin/catalog/")
print("    admin@sonabel-demo.com / admin123")
print("=" * 60)
