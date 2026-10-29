"""Recree les 3 DA de demo + teste le workflow complet."""
import os
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.base"
os.environ["ZIONPAY_MODE"] = "desktop"

import django
django.setup()

from datetime import date, timedelta
from apps.accounts.models import User
from apps.da.models import PurchaseRequest, PurchaseRequestItem, DAItem, DACategory
from apps.notifications.models import Notification
from apps.da import workflow

print("=" * 70)
print("  RECREATION DES DA DE DEMO")
print("=" * 70)

# 1. Nettoyer les anciennes DA et notifications orphelines
old_count = PurchaseRequest.objects.count()
PurchaseRequest.objects.all().delete()
notif_da = Notification.objects.filter(message__icontains="DA-").delete()
print(f"  {old_count} ancienne(s) DA supprimee(s)")

# 2. Recuperer les utilisateurs
chef = User.objects.get(email="chef.maint@sonabel-demo.com")
dir_service = User.objects.get(email="dir.tech@sonabel-demo.com")
dir_achats = User.objects.get(email="achats@sonabel-demo.com")
dg = User.objects.get(email="admin@sonabel-demo.com")
org = chef.organization

# 3. Categories et items
cat = DACategory.objects.filter(organization=org).first()
if not cat:
    cat = DACategory.objects.create(organization=org, name="Fournitures Informatiques")

items = list(DAItem.objects.filter(organization=org)[:3])
if len(items) < 3:
    item1, _ = DAItem.objects.get_or_create(
        organization=org, name="Ordinateur portable HP",
        defaults={"unit_price": 450000, "unit": "PCS", "stock_quantity": 10,
                  "reorder_level": 2, "is_active": True, "is_available_to_all": True,
                  "category": cat}
    )
    item2, _ = DAItem.objects.get_or_create(
        organization=org, name="Imprimante Laser",
        defaults={"unit_price": 150000, "unit": "PCS", "stock_quantity": 5,
                  "reorder_level": 1, "is_active": True, "is_available_to_all": True,
                  "category": cat}
    )
    items = [item1, item2]

# ═══════════════════════════════════════════════════════════════
# CREER 4 DA AVEC DES STATUTS DIFFERENTS
# ═══════════════════════════════════════════════════════════════

# DA 1 : BROUILLON (modifiable par le chef)
da1 = PurchaseRequest.objects.create(
    organization=org, number="DA-2026-0001", requester=chef, service=chef.service,
    purpose="Achat de materiel de bureau (BROUILLON)",
    status="BROUILLON", priority="NORMALE", total_amount=450000, currency_code="FCFA",
)
PurchaseRequestItem.objects.create(request=da1, item=items[0], quantity=1, unit_price=450000, quantity_received=0)
print(f"  ✅ DA 1 : {da1.number} (BROUILLON) - 450 000 FCFA")

# DA 2 : SOUMISE (en attente visa Directeur)
da2 = PurchaseRequest.objects.create(
    organization=org, number="DA-2026-0002", requester=chef, service=chef.service,
    purpose="Achat de 2 ordinateurs pour la Maintenance (en attente visa Directeur)",
    status="SOUMISE", priority="HAUTE", total_amount=900000, currency_code="FCFA",
)
PurchaseRequestItem.objects.create(request=da2, item=items[0], quantity=2, unit_price=450000, quantity_received=0)
print(f"  ✅ DA 2 : {da2.number} (SOUMISE - attend visa Directeur) - 900 000 FCFA")

# DA 3 : VISEE_DIRECTEUR (en attente visa Achats)
da3 = PurchaseRequest.objects.create(
    organization=org, number="DA-2026-0003", requester=chef, service=chef.service,
    purpose="Achat de 3 imprimantes (visé Directeur, attend visa Achats)",
    status="VISEE_DIRECTEUR", priority="NORMALE", total_amount=450000, currency_code="FCFA",
)
PurchaseRequestItem.objects.create(request=da3, item=items[1], quantity=3, unit_price=150000, quantity_received=0)
print(f"  ✅ DA 3 : {da3.number} (VISEE_DIRECTEUR - attend visa Achats) - 450 000 FCFA")

# DA 4 : STOCK_VERIFIE (en attente visa Achats)
da4 = PurchaseRequest.objects.create(
    organization=org, number="DA-2026-0004", requester=chef, service=chef.service,
    purpose="Achat de 5 imprimantes (stock verifie, attend visa Achats)",
    status="STOCK_VERIFIE", priority="HAUTE", total_amount=750000, currency_code="FCFA",
)
PurchaseRequestItem.objects.create(request=da4, item=items[1], quantity=5, unit_price=150000, quantity_received=0)
print(f"  ✅ DA 4 : {da4.number} (STOCK_VERIFIE - attend visa Achats) - 750 000 FCFA")

# DA 5 : VISEE_ACHATS (en attente signature DG)
da5 = PurchaseRequest.objects.create(
    organization=org, number="DA-2026-0005", requester=chef, service=chef.service,
    purpose="Achat de 2 PC portables (visé Achats, attend signature DG)",
    status="VISEE_ACHATS", priority="HAUTE", total_amount=900000, currency_code="FCFA",
)
PurchaseRequestItem.objects.create(request=da5, item=items[0], quantity=2, unit_price=450000, quantity_received=0)
print(f"  ✅ DA 5 : {da5.number} (VISEE_ACHATS - attend signature DG) - 900 000 FCFA")

# DA 6 : VALIDEE (historique)
da6 = PurchaseRequest.objects.create(
    organization=org, number="DA-2026-0006", requester=chef, service=chef.service,
    purpose="Achat de 1 PC portable (deja VALIDEE)",
    status="VALIDEE", priority="NORMALE", total_amount=450000, currency_code="FCFA",
    validated_by=dg, validated_at=django.utils.timezone.now() - timedelta(days=2),
)
PurchaseRequestItem.objects.create(request=da6, item=items[0], quantity=1, unit_price=450000, quantity_received=0)
print(f"  ✅ DA 6 : {da6.number} (VALIDEE - historique) - 450 000 FCFA")

# ═══════════════════════════════════════════════════════════════
# TEST DU FLUX COMPLET
# ═══════════════════════════════════════════════════════════════
print()
print("=" * 70)
print("  TEST DU FLUX COMPLET")
print("=" * 70)

# Test 1 : Visa Directeur sur DA 2 (SOUMISE)
print(f"\n  Test 1 : Visa Directeur sur {da2.number} (SOUMISE)")
try:
    workflow.visa_by_director(da2, actor=dir_service, approved=True)
    da2.refresh_from_db()
    print(f"    → {da2.status} ✅")
except Exception as e:
    print(f"    → ERREUR : {e}")

# Test 2 : Visa Achats sur DA 3 (VISEE_DIRECTEUR)
print(f"\n  Test 2 : Visa Achats sur {da3.number} (VISEE_DIRECTEUR)")
try:
    workflow.visa_by_achats(da3, actor=dir_achats, approved=True)
    da3.refresh_from_db()
    print(f"    → {da3.status} ✅")
except Exception as e:
    print(f"    → ERREUR : {e}")

# ═══════════════════════════════════════════════════════════════
# RAPPORT FINAL
# ═══════════════════════════════════════════════════════════════
print()
print("=" * 70)
print("  ✅ DA DE DEMO PRETES")
print("=" * 70)

print(f"\n  Total DA en base : {PurchaseRequest.objects.count()}")

print("\n  LISTE DES DA PAR STATUT :")
from collections import Counter
statuses = Counter(PurchaseRequest.objects.values_list("status", flat=True))
for status, count in statuses.items():
    print(f"    · {status:<20} : {count}")

print("\n  URLS POUR LA DEMO :")
print("  ─────────────────────────────────────────────────────")
print("  Connecte-toi en tant que :")
print("    · Chef         : chef.maint@sonabel-demo.com / chef123")
print("      → voit DA-0001 (BROUILLON) et DA-0002 (SOUMISE)")
print("    · Directeur    : dir.tech@sonabel-demo.com / dir123")
print("      → voit DA-0002 (SOUMISE) pour la viser")
print("    · Achats       : achats@sonabel-demo.com / achats123")
print("      → voit DA-0003 (VISEE_DIRECTEUR) pour verif stock + visa")
print("      → voit DA-0004 (STOCK_VERIFIE) pour visa")
print("    · DG           : admin@sonabel-demo.com / admin123")
print("      → voit DA-0005 (VISEE_ACHATS) pour signature finale")
print("  ─────────────────────────────────────────────────────")
print("\n  Scénario démo recommandé :")
print("  1. Chef crée une NOUVELLE DA (montre le formulaire)")
print("  2. Directeur vise (montre le visa Directeur)")
print("  3. Achats vérifie stock + vise (montre l'analyse stock)")
print("  4. DG signe (montre la signature finale)")
print("  5. PDF avec QR code + signature (montre le résultat)")
print()
print("=" * 70)
