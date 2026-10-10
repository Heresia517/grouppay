"""Test direct : conversion cle + envoi push."""
import os
import django
import base64

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

from django.conf import settings
from cryptography.hazmat.primitives import serialization

print()
print("=" * 72)
print("  TEST CONVERSION CLE VAPID")
print("=" * 72)

# Charger la cle
private_raw = settings.VAPID_PRIVATE_KEY
print()
print(f">>> Cle brute : {len(private_raw)} chars")
print(f"    Commence par : {private_raw[:40]}...")

# Test conversion
from apps.notifications.push_service import _normalize_vapid_key

converted = _normalize_vapid_key(private_raw)
print()
print(f">>> Cle convertie : {len(converted)} chars")
print(f"    Commence par : {converted[:40]}...")

# Test pywebpush peut la lire
try:
    from py_vapid import Vapid
    vapid_obj = Vapid.from_string(private_key=converted)
    print()
    print("  OK py_vapid peut lire la cle convertie !")
    print(f"    Type : {type(vapid_obj).__name__}")

    # Recuperer l'email claims
    claims = {"sub": "mailto:admin@grouppay.app"}
    print(f"  OK Claims : {claims}")

except Exception as e:
    print()
    print(f"  XX Erreur py_vapid : {e}")

print()
print("=" * 72)
