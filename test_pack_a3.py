"""Test automatisé — PACK A3 : SMS + Emails enrichis + Espace fournisseur."""
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
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse, NoReverseMatch
from django.utils import timezone

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

print()
print("╔" + "═" * 68 + "╗")
print("║" + "  TEST PACK A3 — SMS + Emails + Espace fournisseur".center(68) + "║")
print("║" + f"  {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}".center(68) + "║")
print("╚" + "═" * 68 + "╝")

# ═══════════════════════════════════════════════════════════════
# TEST 1 — SMS Service
# ═══════════════════════════════════════════════════════════════
h1("TEST 1 — SERVICE SMS")

h2("1.1 Fichier sms_service.py")
p = ROOT / "apps/notifications/sms_service.py"
if not p.exists():
    ko("sms_service.py introuvable")
else:
    src = p.read_text(encoding="utf-8")
    for fn in ["def send_sms", "def send_order_validated_sms",
               "def send_order_delivered_sms", "def send_order_rejected_sms"]:
        if fn in src:
            ok(f"{fn} présent")
        else:
            ko(f"{fn} manquant")

h2("1.2 Import du module")
try:
    from apps.notifications.sms_service import send_sms, send_order_validated_sms
    ok("sms_service importable")
except Exception as e:
    ko(f"Import impossible : {e}")

h2("1.3 send_sms() fonctionne (mode console)")
try:
    from apps.notifications.sms_service import send_sms
    result = send_sms("+22670000000", "Test ZionPay SMS")
    if result is True:
        ok("send_sms() retourne True (mode console)")
    else:
        ko(f"send_sms() retourne {result}")
except Exception as e:
    ko(f"Erreur send_sms : {e}")

# ═══════════════════════════════════════════════════════════════
# TEST 2 — Templates Emails
# ═══════════════════════════════════════════════════════════════
h1("TEST 2 — TEMPLATES EMAILS")

emails_to_check = {
    "templates/emails/order_validated.html": ["Commande validée", "order_number"],
    "templates/emails/order_delivered.html": ["Commande livrée", "order_number"],
    "templates/emails/order_rejected.html": ["Commande refusée", "reason", "order_number"],
    "templates/emails/order_shipping.html": ["En cours de livraison", "order_number"],
}

for path, needles in emails_to_check.items():
    h2(f"2.x {path}")
    p = ROOT / path
    if not p.exists():
        ko(f"{path} introuvable")
        continue
    src = p.read_text(encoding="utf-8")
    for needle in needles:
        if needle in src:
            ok(f"contient '{needle}'")
        else:
            ko(f"MANQUE '{needle}'")

# ═══════════════════════════════════════════════════════════════
# TEST 3 — Email Service étendu
# ═══════════════════════════════════════════════════════════════
h1("TEST 3 — EMAIL SERVICE")

p = ROOT / "apps/notifications/email_service.py"
if p.exists():
    src = p.read_text(encoding="utf-8")
    for fn in ["def send_order_rejected_email", "def send_order_shipping_email"]:
        if fn in src:
            ok(f"{fn} présent")
        else:
            ko(f"{fn} manquant")

h2("3.1 Import")
try:
    from apps.notifications.email_service import (
        send_order_rejected_email, send_order_shipping_email,
    )
    ok("Import OK")
except Exception as e:
    ko(f"Import impossible : {e}")

# ═══════════════════════════════════════════════════════════════
# TEST 4 — Signals
# ═══════════════════════════════════════════════════════════════
h1("TEST 4 — SIGNALS")

p = ROOT / "apps/notifications/signals.py"
if p.exists():
    src = p.read_text(encoding="utf-8")
    checks = [
        ("send_sms_on_status_change", "signal SMS"),
        ("send_extra_emails", "signal emails additionnels"),
        ("send_order_rejected_sms", "SMS refusée"),
        ("send_order_shipping_email", "email en livraison"),
    ]
    for needle, label in checks:
        if needle in src:
            ok(f"{label} présent")
        else:
            ko(f"{label} manquant")

# ═══════════════════════════════════════════════════════════════
# TEST 5 — Settings SMS
# ═══════════════════════════════════════════════════════════════
h1("TEST 5 — SETTINGS")

if hasattr(settings, "AFRICASTALKING_USERNAME"):
    ok(f"AFRICASTALKING_USERNAME = '{settings.AFRICASTALKING_USERNAME}' (vide en dev = fallback console)")
else:
    ko("AFRICASTALKING_USERNAME manquant")

if hasattr(settings, "AFRICASTALKING_API_KEY"):
    ok("AFRICASTALKING_API_KEY présent")
else:
    ko("AFRICASTALKING_API_KEY manquant")

# ═══════════════════════════════════════════════════════════════
# TEST 6 — Espace fournisseur
# ═══════════════════════════════════════════════════════════════
h1("TEST 6 — ESPACE FOURNISSEUR")

h2("6.1 Fichier supplier_views.py")
p = ROOT / "apps/catalog/supplier_views.py"
if not p.exists():
    ko("supplier_views.py introuvable")
else:
    src = p.read_text(encoding="utf-8")
    if "def supplier_dashboard" in src:
        ok("def supplier_dashboard présent")
    else:
        ko("def supplier_dashboard manquant")
    if "_require_supplier" in src:
        ok("Permission check _require_supplier présent")
    else:
        ko("_require_supplier manquant")

h2("6.2 Template supplier_dashboard.html")
p = ROOT / "templates/catalog/supplier_dashboard.html"
if not p.exists():
    ko("Template introuvable")
else:
    src = p.read_text(encoding="utf-8")
    for needle in ["Espace fournisseur", "Mes produits", "Top 5"]:
        if needle in src:
            ok(f"contient '{needle}'")
        else:
            ko(f"MANQUE '{needle}'")

h2("6.3 URL /supplier/")
try:
    url = reverse("supplier_dashboard")
    if "/supplier/" in url:
        ok(f"URL OK : {url}")
    else:
        warn(f"URL : {url}")
except NoReverseMatch:
    ko("URL supplier_dashboard non trouvée")

# ═══════════════════════════════════════════════════════════════
# TEST 7 — FONCTIONNEL : Envoi SMS réels
# ═══════════════════════════════════════════════════════════════
h1("TEST 7 — FONCTIONNEL : SMS")

user = User.objects.filter(is_superuser=True).first()
if not user:
    ko("Aucun superuser")
else:
    from apps.orders.models import Order

    order = Order.objects.filter(organization=user.organization).first()
    if not order:
        warn("Aucune commande pour tester")
    else:
        # Simuler un phone
        order.member.phone = "+22670000000"
        order.member.save(update_fields=["phone"])

        h2("7.1 send_order_validated_sms")
        try:
            from apps.notifications.sms_service import send_order_validated_sms
            result = send_order_validated_sms(order)
            if result is True:
                ok(f"SMS validée envoyé pour {order.order_number}")
            else:
                ko(f"Échec (résultat: {result})")
        except Exception as e:
            ko(f"Erreur : {e}")

        h2("7.2 send_order_delivered_sms")
        try:
            from apps.notifications.sms_service import send_order_delivered_sms
            result = send_order_delivered_sms(order)
            if result is True:
                ok(f"SMS livrée envoyé")
            else:
                ko(f"Échec")
        except Exception as e:
            ko(f"Erreur : {e}")

# ═══════════════════════════════════════════════════════════════
# TEST 8 — FONCTIONNEL : Emails réels (outbox)
# ═══════════════════════════════════════════════════════════════
h1("TEST 8 — FONCTIONNEL : EMAILS")

if user:
    from django.test.utils import override_settings
    from django.core import mail

    with override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
        from apps.notifications.email_service import (
            send_order_rejected_email, send_order_shipping_email,
        )

        h2("8.1 send_order_rejected_email")
        try:
            mail.outbox = []
            result = send_order_rejected_email(order, "Test motif")
            if result and len(mail.outbox) == 1:
                ok(f"Email refusée envoyé ({mail.outbox[0].subject})")
            else:
                ko(f"Échec (résultat={result}, outbox={len(mail.outbox)})")
        except Exception as e:
            ko(f"Erreur : {e}")

        h2("8.2 send_order_shipping_email")
        try:
            mail.outbox = []
            result = send_order_shipping_email(order)
            if result and len(mail.outbox) == 1:
                ok(f"Email livraison envoyé ({mail.outbox[0].subject})")
            else:
                ko(f"Échec")
        except Exception as e:
            ko(f"Erreur : {e}")

# ═══════════════════════════════════════════════════════════════
# TEST 9 — FONCTIONNEL : Dashboard fournisseur HTTP
# ═══════════════════════════════════════════════════════════════
h1("TEST 9 — HTTP : DASHBOARD FOURNISSEUR")

if user:
    h2("9.1 GET /supplier/ (ADMIN)")
    try:
        c = Client()
        c.force_login(user)
        r = c.get("/supplier/")
        if r.status_code == 200:
            content = r.content.decode("utf-8")
            if "Espace fournisseur" in content:
                ok(f"Dashboard fournisseur → 200 ({len(content)} bytes)")
            else:
                warn("Contenu inattendu")
        else:
            ko(f"HTTP {r.status_code}")
    except Exception as e:
        ko(f"Erreur : {e}")

    h2("9.2 Permission : MEMBRE bloqué")
    try:
        member = User.objects.filter(role="MEMBRE").first()
        if member:
            c = Client()
            c.force_login(member)
            r = c.get("/supplier/")
            if r.status_code in (403, 302):
                ok(f"MEMBRE → {r.status_code} (correct)")
            else:
                warn(f"MEMBRE → {r.status_code} (attendu 403)")
        else:
            warn("Aucun membre pour tester")
    except Exception as e:
        ko(f"Erreur : {e}")

# ═══════════════════════════════════════════════════════════════
# TEST 10 — Navbar
# ═══════════════════════════════════════════════════════════════
h1("TEST 10 — NAVBAR")

p = ROOT / "templates/components/navbar.html"
if p.exists():
    src = p.read_text(encoding="utf-8")
    if "supplier_dashboard" in src:
        ok("Lien 'Espace fournisseur' présent")
    else:
        ko("Lien 'Espace fournisseur' MANQUANT")
    if "url 'deductions_dashboard'" in src:
        ok("Lien 'Retenue salariale' présent")
    else:
        ko("Lien 'Retenue' MANQUANT")

# ═══════════════════════════════════════════════════════════════
# TEST 11 — Cohérence
# ═══════════════════════════════════════════════════════════════
h1("TEST 11 — COHÉRENCE")

h2("11.1 Django check")
try:
    from django.core.management import call_command
    from io import StringIO
    out = StringIO()
    call_command("check", stdout=out, stderr=out)
    ok("Django check OK")
except Exception as e:
    ko(f"check échoue : {e}")

h2("11.2 Migrations en attente")
try:
    from django.core.management import call_command
    from io import StringIO
    out = StringIO()
    try:
        call_command("makemigrations", "--check", "--dry-run", stdout=out, stderr=out)
        ok("Aucune migration en attente")
    except SystemExit:
        warn("Migrations en attente — lance: python manage.py makemigrations")
except Exception as e:
    warn(f"Impossible : {e}")

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
    print("  🎉 PACK A3 — TOUS LES TESTS PASSENT")
    print("  → PACK A complet ! On peut passer au PACK B (Marketplace)")
elif results["failed"] <= 2:
    print("  ⚠️  PACK A3 — Quelques échecs mineurs")
else:
    print("  ❌ PACK A3 — Plusieurs échecs")

if results["failed"] > 0 or results["warned"] > 0:
    print()
    print("  📋 Détails des problèmes :")
    for status, msg in results["details"]:
        if status in ("FAIL", "WARN"):
            icon = "❌" if status == "FAIL" else "⚠️"
            print(f"     {icon} {msg}")

print()
print("═" * 70)
