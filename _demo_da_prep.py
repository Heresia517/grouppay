"""Prepare le module DA pour la demo : tests + donnees de demo."""
import os
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.base"
os.environ["ZIONPAY_MODE"] = "desktop"

import django
django.setup()

import inspect
from django.test import Client
from apps.accounts.models import User
from apps.da.models import PurchaseRequest, DAItem, DACategory, PurchaseRequestItem

print("=" * 70)
print("  PREPARATION DU MODULE DA (DEMANDES D'ACHAT) POUR LA DEMO")
print("=" * 70)

# 1. ETAT ACTUEL
print("\n--- 1. ETAT ACTUEL ---")
print(f"  Demandes d'achat en base : {PurchaseRequest.objects.count()}")
print(f"  Categories DA : {DACategory.objects.count()}")
print(f"  Items DA : {DAItem.objects.count()}")

# 2. CREER DES DONNEES DE DEMO SI VIDE
if PurchaseRequest.objects.count() == 0:
    print("\n  → Aucune DA en base. Creation de 2 demandes de demo...")
    
    chef = User.objects.get(email="chef.maint@sonabel-demo.com")
    org = chef.organization
    
    # Categorie
    cat, _ = DACategory.objects.get_or_create(
        organization=org, name="Fournitures Informatiques"
    )
    
    # Items
    item1, _ = DAItem.objects.get_or_create(
        organization=org, category=cat, name="Ordinateur portable HP",
        defaults={"unit_price": 450000}
    )
    item2, _ = DAItem.objects.get_or_create(
        organization=org, category=cat, name="Imprimante Laser",
        defaults={"unit_price": 150000}
    )
    
    # DA 1 (En attente de Visa)
    da1 = PurchaseRequest.objects.create(
        organization=org,
        requester=chef,
        title="Achat de 2 ordinateurs portables pour le service Maintenance",
        status="PENDING_VISA", # ou le statut initial exact
        total_amount=900000,
    )
    PurchaseRequestItem.objects.create(da=da1, item=item1, quantity=2, unit_price=450000)
    print(f"  ✅ DA 1 creee : {da1.title} (En attente de Visa)")
    
    # DA 2 (Brouillon)
    da2 = PurchaseRequest.objects.create(
        organization=org,
        requester=chef,
        title="Renouvellement des imprimantes",
        status="DRAFT",
        total_amount=150000,
    )
    PurchaseRequestItem.objects.create(da=da2, item=item2, quantity=1, unit_price=150000)
    print(f"  ✅ DA 2 creee : {da2.title} (Brouillon)")
else:
    print("\n  → Donnees DA deja presentes, on ne recree pas.")

# 3. TESTER LE FLUX AVEC LES CLIENTS DJANGO
print("\n--- 2. TEST DU FLUX (Chef -> Directeur -> DG) ---")

chef = User.objects.get(email="chef.maint@sonabel-demo.com")
directeur = User.objects.get(email="dir.tech@sonabel-demo.com")
dg = User.objects.get(email="admin@sonabel-demo.com")

# 3a. Test Chef
c_chef = Client(SERVER_NAME="127.0.0.1")
c_chef.force_login(chef)
r = c_chef.get("/da/")
print(f"  [Chef] GET /da/ -> HTTP {r.status_code}")

# 3b. Test Directeur
c_dir = Client(SERVER_NAME="127.0.0.1")
c_dir.force_login(directeur)
r = c_dir.get("/da/")
print(f"  [Directeur] GET /da/ -> HTTP {r.status_code}")

# 3c. Test DG
c_dg = Client(SERVER_NAME="127.0.0.1")
c_dg.force_login(dg)
r = c_dg.get("/da/")
print(f"  [DG] GET /da/ -> HTTP {r.status_code}")

# 3d. Test d'une DA specifique
da = PurchaseRequest.objects.first()
if da:
    r = c_chef.get(f"/da/{da.id}/")
    print(f"  [Chef] GET /da/{{id}}/ -> HTTP {r.status_code}")
    
    # 3e. Test PDF
    r = c_chef.get(f"/da/{da.id}/pdf/")
    print(f"  [Chef] GET /da/{{id}}/pdf/ -> HTTP {r.status_code}")

print()
print("=" * 70)
print("  ✅ MODULE DA PRET POUR LA DEMO")
print("=" * 70)
print("""
  SCRIPT DE DEMO POUR LA DA :
  
  1. Connecte-toi en Chef : chef.maint@sonabel-demo.com / chef123
  2. Va sur l'espace DA (/da/).
  3. Montre la liste des demandes et leur statut (En attente de Visa / Brouillon).
  4. Ouvre une DA, montre le détail (produits, montants en FCFA).
  5. Télécharge le PDF de la DA.
  6. (Optionnel) Montre le parcours d'approbation :
     - Connecte-toi en Directeur (dir.tech@sonabel-demo.com) pour le Visa.
     - Connecte-toi en DG (admin@sonabel-demo.com) pour la signature finale.
""")
print("=" * 70)
