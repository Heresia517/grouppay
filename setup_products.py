"""Créer les produits avec les vrais champs du modèle."""
import os, sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.base")
os.environ["GROUPPAY_MODE"] = "desktop"

import django
django.setup()

from decimal import Decimal
from apps.organizations.models import Organization
from apps.accounts.models import User
from apps.catalog.models import Category, Product, Coupon
from django.utils import timezone
from datetime import timedelta


org = Organization.objects.first()
if not org:
    print("Aucune organisation. Lance : python manage.py seed_users")
    sys.exit(1)

suppliers = list(User.objects.filter(email__in=[
    "fournisseur1@sonabel-demo.com", "fournisseur2@sonabel-demo.com"
]))
print(f"Organisation : {org.name}")
print(f"Fournisseurs : {len(suppliers)}\n")

# Mapping slug catégorie → objet
cats = {c.slug: c for c in Category.objects.filter(organization=org)}
print(f"Catégories disponibles : {len(cats)}\n")


PRODUITS = [
    # (nom, categorie_slug, prix_vente, prix_cout, stock, description)
    ("Riz parfumé 25 kg", "alimentation", 18500, 15000, 100, "Sac de riz parfumé 25 kg"),
    ("Huile végétale 5 L", "alimentation", 6250, 5000, 200, "Huile de cuisine 5 litres"),
    ("Sucre en poudre 1 kg", "alimentation", 700, 550, 500, "Sucre blanc granulé"),
    ("Pâtes alimentaires 500 g", "alimentation", 450, 350, 800, "Spaghetti / macaroni"),
    ("Lait en poudre 400 g", "alimentation", 3500, 2800, 150, "Lait en poudre instantané"),
    ("Tomate concentrée 400 g", "alimentation", 650, 500, 600, "Boîte de concentré"),
    ("Savon de Marseille 400 g", "alimentation", 500, 400, 1000, "Savon multi-usage"),

    ("Savon de toilette x6", "hygiene-soins", 1800, 1400, 300, "Lot de 6 savons parfumés"),
    ("Dentifrice 100 ml", "hygiene-soins", 900, 700, 400, "Dentifrice au fluor"),
    ("Détergent lessive 5 kg", "hygiene-soins", 4500, 3600, 200, "Poudre à lessive"),
    ("Eau de javel 1 L", "hygiene-soins", 550, 400, 500, "Javel concentrée"),
    ("Papier hygiénique x12", "hygiene-soins", 2500, 2000, 250, "Lot de 12 rouleaux"),

    ("Ventilateur sur pied", "electromenager", 22000, 18000, 30, "Ventilateur 3 vitesses"),
    ("Fer à repasser", "electromenager", 12500, 10000, 50, "Fer vapeur 1200 W"),
    ("Bouilloire électrique", "electromenager", 8500, 7000, 80, "Bouilloire 1,7 L"),
    ("Mixeur plongeant", "electromenager", 15000, 12000, 40, "Mixeur 400 W"),
    ("Réfrigérateur 150 L", "electromenager", 185000, 160000, 10, "Réfrigérateur 2 portes"),

    ("Pagne wax 6 yards", "textile", 8500, 7000, 200, "Pagne wax authentique"),
    ("Drap 2 places", "textile", 6500, 5000, 150, "Drap coton 220x240"),
    ("Serviette de bain", "textile", 3500, 2800, 250, "Serviette éponge 70x140"),
    ("Moustiquaire imprégnée", "textile", 4500, 3500, 400, "Moustiquaire 2 places"),

    ("Cahier 200 pages", "papeterie", 350, 250, 1000, "Cahier grand format"),
    ("Stylo bille bleu x10", "papeterie", 500, 350, 800, "Lot de 10 stylos"),
    ("Ramette A4 500 feuilles", "papeterie", 3500, 2800, 200, "Papier A4 80g"),
    ("Classeur à levier", "papeterie", 1200, 900, 300, "Classeur A4 dos 7 cm"),

    ("Téléphone basique", "electronique", 15000, 12000, 60, "Téléphone 2G simple"),
    ("Radio FM portative", "electronique", 8500, 7000, 80, "Radio AM/FM"),
    ("Écouteurs filaires", "electronique", 1500, 1000, 400, "Écouteurs jack 3,5 mm"),
    ("Chargeur universel", "electronique", 2500, 1800, 250, "Chargeur USB multi-embouts"),
    ("Lampe torche LED", "electronique", 2000, 1500, 300, "Lampe rechargeable"),

    ("Chaise plastique", "mobilier", 4500, 3500, 200, "Chaise monobloc"),
    ("Table pliante", "mobilier", 18000, 15000, 40, "Table 120x60 cm"),
    ("Armoire 2 portes", "mobilier", 75000, 65000, 15, "Armoire en bois"),
    ("Matelas 2 places", "mobilier", 35000, 28000, 25, "Matelas mousse 140x190"),

    ("Ciment 50 kg", "construction", 5500, 4500, 500, "Sac de ciment CPJ 35"),
    ("Peinture blanche 5 L", "construction", 12500, 10000, 60, "Peinture acrylique"),
    ("Fer à béton 12 mm", "construction", 4500, 3800, 300, "Barre de fer 12 m"),
    ("Clous 5 cm 1 kg", "construction", 1500, 1200, 400, "Clous acier"),
]

created = 0
skipped = 0
for i, (name, cat_slug, price, cost, stock, desc) in enumerate(PRODUITS, start=1):
    sku = f"GP-{i:04d}"
    supplier = suppliers[i % len(suppliers)] if suppliers else None

    if Product.objects.filter(organization=org, sku=sku).exists():
        skipped += 1
        continue

    Product.objects.create(
        organization=org,
        category=cats.get(cat_slug),
        name=name,
        sku=sku,
        description=desc,
        price=Decimal(str(price)),
        cost_price=Decimal(str(cost)),
        stock_quantity=stock,
        reorder_level=max(5, stock // 10),
        is_active=True,
        supplier=supplier,
        max_per_member=10,
        lead_time_days=7,
    )
    created += 1

print(f"[OK] {created} produits créés ({skipped} déjà existants)")
print(f"     Total en base : {Product.objects.count()}\n")

# ═══════════════════════════════════════════════════════════════
# COUPONS
# ═══════════════════════════════════════════════════════════════
now = timezone.now()
coupon_fields = {f.name for f in Coupon._meta.get_fields() if hasattr(f, "attname")}
print(f"Champs Coupon : {sorted(coupon_fields)}\n")

COUPONS = [
    ("BIENVENUE10", "10% sur la 1ère commande", 10),
    ("RENTREE5000", "-5000 FCFA dès 50 000", 10),
    ("FIDELE15", "15% pour les membres fidèles", 15),
]

cc = 0
for code, desc, pct in COUPONS:
    if Coupon.objects.filter(organization=org, code=code).exists():
        continue
    kwargs = {
        "organization": org,
        "code": code,
        "description": desc,
        "discount_type": "percentage",
        "discount_value": Decimal(str(pct)),
        "discount_percent": pct,
        "valid_from": now,
        "valid_until": now + timedelta(days=90),
        "is_active": True,
        "max_uses": 100,
        "min_order_amount": Decimal("0"),
    }
    # Filtrer sur les champs réels
    kwargs = {k: v for k, v in kwargs.items() if k in coupon_fields}
    try:
        Coupon.objects.create(**kwargs)
        cc += 1
    except Exception as e:
        print(f"  Erreur coupon {code}: {e}")

print(f"[OK] {cc} coupons créés (total {Coupon.objects.count()})\n")

# ═══════════════════════════════════════════════════════════════
# RÉSUMÉ
# ═══════════════════════════════════════════════════════════════
print("=" * 60)
print("  CATALOGUE DE DÉMONSTRATION — PRÊT")
print("=" * 60)
print(f"  Catégories : {Category.objects.count()}")
print(f"  Produits   : {Product.objects.count()}")
print(f"  Coupons    : {Coupon.objects.count()}")
print()
for cat in Category.objects.filter(organization=org):
    n = Product.objects.filter(organization=org, category=cat).count()
    print(f"  · {cat.name:<20} {n:>2} produits")
print("=" * 60)
