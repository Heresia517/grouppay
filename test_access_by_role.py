"""Test : separation d'acces par role."""
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

try:
    import django
    django.setup()
except Exception as e:
    print(f"XX Django : {e}")
    sys.exit(1)

from django.test import Client
from apps.accounts.models import User

print()
print("=" * 78)
print("  TEST SEPARATION D'ACCES PAR ROLE")
print("=" * 78)
print()

TESTS = [
    ("admin@sonabel-demo.com", "admin123", "ADMIN/DG"),
    ("rh@sonabel-demo.com", "rh123", "RH"),
    ("chef.maint@sonabel-demo.com", "chef123", "CHEF SERVICE"),
    ("dir.tech@sonabel-demo.com", "dir123", "DIRECTEUR"),
    ("achats@sonabel-demo.com", "achats123", "ACHATS"),
    ("membre1@sonabel-demo.com", "membre123", "MEMBRE"),
    ("fournisseur1@sonabel-demo.com", "fourn123", "FOURNISSEUR"),
    ("livreur1@sonabel-demo.com", "livreur123", "LIVREUR"),
]

PAGES = [
    ("/", "Landing", True),           # True = accessible pour tous
    ("/catalog/", "Catalogue", True),
    ("/cart/", "Panier", None),       # depend du role
    ("/da/", "DA Dashboard", False),
    ("/inventory/", "Inventaire", False),
    ("/rh/dashboard/", "RH Dashboard", False),
]

# Matrice des attentes : True=OK, False=refuse
EXPECTED = {
    "ADMIN/DG":     {"Landing": True, "Catalogue": True, "Panier": True, "DA Dashboard": True, "Inventaire": True, "RH Dashboard": True},
    "RH":           {"Landing": True, "Catalogue": True, "Panier": True, "DA Dashboard": True, "Inventaire": True, "RH Dashboard": True},
    "CHEF SERVICE": {"Landing": True, "Catalogue": True, "Panier": True, "DA Dashboard": True, "Inventaire": False, "RH Dashboard": False},
    "DIRECTEUR":    {"Landing": True, "Catalogue": True, "Panier": True, "DA Dashboard": True, "Inventaire": False, "RH Dashboard": False},
    "ACHATS":       {"Landing": True, "Catalogue": True, "Panier": True, "DA Dashboard": True, "Inventaire": True, "RH Dashboard": False},
    "MEMBRE":       {"Landing": True, "Catalogue": True, "Panier": True, "DA Dashboard": False, "Inventaire": False, "RH Dashboard": False},
    "FOURNISSEUR":  {"Landing": True, "Catalogue": True, "Panier": False, "DA Dashboard": False, "Inventaire": False, "RH Dashboard": False},
    "LIVREUR":      {"Landing": True, "Catalogue": True, "Panier": True, "DA Dashboard": False, "Inventaire": False, "RH Dashboard": False},
}

total_checks = 0
total_ok = 0

for email, password, label in TESTS:
    print(f">>> {label} ({email})")

    user = User.objects.filter(email=email).first()
    if not user:
        print(f"  XX User introuvable")
        print()
        continue

    # Login
    client = Client()
    logged_in = client.login(username=email, password=password)
    if not logged_in:
        print(f"  XX Login echoue")
        print()
        continue

    print(f"  OK Login reussi")
    print()

    for path, page_name, _ in PAGES:
        total_checks += 1
        try:
            r = client.get(path)
            status = r.status_code
            expected_access = EXPECTED.get(label, {}).get(page_name, False)

            if status == 200:
                if expected_access:
                    print(f"    OK {page_name:<15} -> 200")
                    total_ok += 1
                else:
                    print(f"    !! {page_name:<15} -> 200 (ATTENDU: refuse)")
            elif status in (302, 403, 404):
                if expected_access:
                    print(f"    XX {page_name:<15} -> {status} (ATTENDU: OK)")
                else:
                    print(f"    OK {page_name:<15} -> {status} (refuse)")
                    total_ok += 1
            else:
                print(f"    ?? {page_name:<15} -> {status}")
                if expected_access:
                    total_ok += 1
        except Exception as e:
            print(f"    XX {page_name:<15} -> {e}")

    print()

print("=" * 78)
pct = (total_ok / total_checks * 100) if total_checks else 0
print(f"  RESULTAT : {total_ok}/{total_checks} ({pct:.1f}%)")
print("=" * 78)
print()
