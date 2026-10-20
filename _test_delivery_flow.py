"""Test complet du flux de livraison (RH valide -> Livreur livre)."""
import os
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.base"
os.environ["GROUPPAY_MODE"] = "desktop"

import django
django.setup()

from django.test import Client
from apps.accounts.models import User
from apps.orders.models import Order
from apps.deliveries.models import Delivery

print("=" * 70)
print("  TEST DU FLUX LIVRAISON")
print("=" * 70)

# ─── 1. ETAT DES COMMANDES ET LIVRAISONS
print("\n--- 1. ETAT ACTUEL ---")
validees = Order.objects.filter(status="VALIDEE")
print(f"  Commandes VALIDEES a livrer : {validees.count()}")
print(f"  Livraisons en base : {Delivery.objects.count()}")

# ─── 2. CHOISIR UNE COMMANDE VALIDEE
order = validees.first()
if not order:
    print("\n  ⚠️  Aucune commande validee.")
    print("  → Valide d'abord une commande via le RH (ou via le script precedent).")
    raise SystemExit(1)

print(f"\n  Commande cible : {order.order_number}")
print(f"  Montant : {int(order.total_amount):,} FCFA".replace(",", " "))
print(f"  Statut : {order.status}")

# ─── 3. VERIFIER SI UNE LIVRAISON EXISTE
delivery = Delivery.objects.filter(order=order).first()
if not delivery:
    print("\n  ⚠️  Aucune livraison associee a cette commande.")
    print("  → Le signal de creation automatique n'a pas fonctionne.")
    print("  → On cree la livraison manuellement...")
    # Tenter de creer
    try:
        livreur = User.objects.filter(role="LIVREUR").first()
        delivery = Delivery.objects.create(
            order=order,
            courier=livreur,
            status="ASSIGNEE"
        )
        print(f"  ✅ Livraison creee manuellement : {delivery.id}")
    except Exception as e:
        print(f"  ❌ Erreur creation : {e}")
        raise SystemExit(1)
else:
    print(f"\n  ✅ Livraison existante : {delivery.id} (statut: {delivery.status})")

# ─── 4. CONNEXION LIVREUR
print("\n--- 2. CONNEXION LIVREUR ---")
livreur = delivery.courier or User.objects.filter(role="LIVREUR").first()
if not livreur:
    print("  ❌ Aucun livreur trouve.")
    raise SystemExit(1)
print(f"  Livreur : {livreur.email}")

client = Client(SERVER_NAME="127.0.0.1")
client.force_login(livreur)

# ─── 5. LE LIVREUR VOIT-IL SES LIVRAISONS ?
r = client.get("/deliveries/")
print(f"\n  [LIVREUR] Page /deliveries/ -> HTTP {r.status_code}")
if r.status_code == 200:
    html = r.content.decode()
    if str(order.id) in html or order.order_number in html:
        print(f"  ✅ La commande {order.order_number} est visible dans la liste")
    else:
        print(f"  ⚠️  La commande n'apparait pas dans le HTML (filtre trop strict ?)")

# ─── 6. LE LIVREUR MARQUE COMME LIVREE
print(f"\n  [LIVREUR] Mise a jour de la livraison -> LIVREE")
r = client.post(f"/deliveries/{delivery.id}/update/", {"status": "LIVREE", "notes": "Livre au client"})
print(f"  [LIVREUR] POST /deliveries/<id>/update/ -> HTTP {r.status_code}")

# ─── 7. VERIFICATION FINALE
delivery.refresh_from_db()
order.refresh_from_db()

print(f"\n  Statut Livraison : {delivery.status}")
print(f"  Statut Commande  : {order.status}")

if delivery.status == "LIVREE" and order.status == "LIVREE":
    print("\n  ✅ FLUX LIVRAISON PARFAIT !")
    print("     Le livreur a bien livre la commande, le statut est a jour.")
elif delivery.status == "LIVREE" and order.status != "LIVREE":
    print("\n  ⚠️  La livraison est LIVREE, mais la commande n'a pas ete mise a jour.")
    print("     Il manque un signal ou une mise a jour de l'Order dans la vue.")
else:
    print("\n  ❌ La livraison n'a pas ete mise a jour correctement.")

print("\n" + "=" * 70)
