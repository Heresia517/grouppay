"""Test automatisé — Pack A1 : Import CSV membres + Emails réels."""
import os
import sys
from pathlib import Path
from datetime import datetime

# Ajouter le CWD au path
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
from django.core import mail
from django.test import Client
from django.urls import reverse, NoReverseMatch

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

# ═══════════════════════════════════════════════════════════════
# Header
# ═══════════════════════════════════════════════════════════════
print()
print("╔" + "═" * 68 + "╗")
print("║" + "  TEST PACK A1 — Import CSV + Emails".center(68) + "║")
print("║" + f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".center(68) + "║")
print("╚" + "═" * 68 + "╝")

# ═══════════════════════════════════════════════════════════════
# TEST 1 — Vues
# ═══════════════════════════════════════════════════════════════
h1("TEST 1 — VUES")

h2("1.1 apps/accounts/views.py")
p = ROOT / "apps/accounts/views.py"
if p.exists():
    src = p.read_text(encoding="utf-8")
    for fn in ["def import_members_page", "def import_members_csv", "def import_members_template"]:
        if fn in src:
            ok(f"{fn} présent")
        else:
            ko(f"{fn} manquant")
else:
    ko("apps/accounts/views.py introuvable")

h2("1.2 Imports dans le fichier")
if p.exists():
    src = p.read_text(encoding="utf-8")
    for imp in ["import csv", "import io", "import secrets"]:
        if imp in src:
            ok(f"{imp} présent")
        else:
            ko(f"{imp} manquant")

# ═══════════════════════════════════════════════════════════════
# TEST 2 — URLs
# ═══════════════════════════════════════════════════════════════
h1("TEST 2 — URLs")

url_names = [
    ("import_members", "/rh/members/import/"),
    ("import_members_upload", "/rh/members/import/upload/"),
    ("import_members_template", "/rh/members/import/template/"),
]

for name, expected in url_names:
    try:
        url = reverse(name)
        if expected in url:
            ok(f"{name} → {url}")
        else:
            warn(f"{name} → {url} (attendu {expected})")
    except NoReverseMatch:
        ko(f"{name} → NON TROUVÉE")

# ═══════════════════════════════════════════════════════════════
# TEST 3 — Templates
# ═══════════════════════════════════════════════════════════════
h1("TEST 3 — TEMPLATES")

templates_to_check = {
    "templates/admin/import_members.html": [
        "Importer des membres", "csv_file", "Télécharger le modèle",
    ],
    "templates/emails/order_validated.html": [
        "Commande validée", "order_number", "total_amount",
    ],
    "templates/emails/order_delivered.html": [
        "Commande livrée", "order_number",
    ],
}

for path, needles in templates_to_check.items():
    h2(f"3.x {path}")
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
# TEST 4 — Service Email
# ═══════════════════════════════════════════════════════════════
h1("TEST 4 — SERVICE EMAIL")

h2("4.1 Fichier email_service.py")
p = ROOT / "apps/notifications/email_service.py"
if not p.exists():
    ko("apps/notifications/email_service.py introuvable")
else:
    src = p.read_text(encoding="utf-8")
    for fn in ["def send_email", "def send_order_validated_email", "def send_order_delivered_email"]:
        if fn in src:
            ok(f"{fn} présent")
        else:
            ko(f"{fn} manquant")

h2("4.2 Import du module")
try:
    from apps.notifications.email_service import send_email, send_order_validated_email
    ok("Module importable")
except Exception as e:
    ko(f"Import impossible : {e}")

# ═══════════════════════════════════════════════════════════════
# TEST 5 — Settings Email
# ═══════════════════════════════════════════════════════════════
h1("TEST 5 — SETTINGS")

h2("5.1 SITE_URL")
if hasattr(settings, "SITE_URL"):
    ok(f"SITE_URL = {settings.SITE_URL}")
else:
    ko("SITE_URL manquant")

h2("5.2 DEFAULT_FROM_EMAIL")
if hasattr(settings, "DEFAULT_FROM_EMAIL"):
    ok(f"DEFAULT_FROM_EMAIL = {settings.DEFAULT_FROM_EMAIL}")
else:
    ko("DEFAULT_FROM_EMAIL manquant")

h2("5.3 EMAIL_BACKEND")
backend = getattr(settings, "EMAIL_BACKEND", "")
if "console" in backend or "smtp" in backend or "locmem" in backend:
    ok(f"EMAIL_BACKEND = {backend}")
else:
    warn(f"EMAIL_BACKEND = {backend}")

# ═══════════════════════════════════════════════════════════════
# TEST 6 — Signal Email
# ═══════════════════════════════════════════════════════════════
h1("TEST 6 — SIGNAL EMAIL")

p = ROOT / "apps/notifications/signals.py"
if p.exists():
    src = p.read_text(encoding="utf-8")
    if "send_email_on_status_change" in src:
        ok("Signal send_email_on_status_change présent")
    else:
        ko("Signal send_email_on_status_change manquant")
    if "send_order_validated_email" in src:
        ok("Appel send_order_validated_email présent")
    else:
        ko("Appel send_order_validated_email manquant")
else:
    ko("signals.py introuvable")

# ═══════════════════════════════════════════════════════════════
# TEST 7 — FONCTIONNEL : Import CSV
# ═══════════════════════════════════════════════════════════════
h1("TEST 7 — FONCTIONNEL : IMPORT CSV")

user = User.objects.filter(is_superuser=True).first()
if not user:
    ko("Aucun superuser trouvé")
else:
    info(f"Superuser : {user.email}")
    org = user.organization

    # 7.1 Page import
    h2("7.1 GET /rh/members/import/")
    try:
        c = Client()
        c.force_login(user)
        r = c.get(reverse("import_members"))
        if r.status_code == 200:
            content = r.content.decode("utf-8")
            if "Importer des membres" in content:
                ok(f"Page import → 200 ({len(content)} bytes)")
            else:
                warn("Page chargée mais contenu inattendu")
        else:
            ko(f"Page import → {r.status_code}")
    except Exception as e:
        ko(f"Erreur page import : {e}")

    # 7.2 Template CSV
    h2("7.2 GET /rh/members/import/template/")
    try:
        c = Client()
        c.force_login(user)
        r = c.get(reverse("import_members_template"))
        if r.status_code == 200:
            content = r.content.decode("utf-8")
            if "email,first_name" in content:
                ok(f"Template CSV → 200 ({len(content)} bytes)")
            else:
                warn("Contenu CSV inattendu")
        else:
            ko(f"Template CSV → {r.status_code}")
    except Exception as e:
        ko(f"Erreur template : {e}")

    # 7.3 Import réel
    h2("7.3 POST /rh/members/import/upload/ (3 emails)")
    try:
        import io as _io
        from django.core.files.uploadedfile import SimpleUploadedFile

        csv_content = """email,first_name,last_name,internal_id,role
__test_a1_1@test.local,Jean,Dupont,TESTA1_001,MEMBRE
__test_a1_2@test.local,Marie,Kone,TESTA1_002,MEMBRE
__test_a1_3@test.local,Paul,Traore,TESTA1_003,MEMBRE
"""
        # Nettoyer avant
        User.objects.filter(email__startswith="__test_a1_").delete()

        csv_file = SimpleUploadedFile("test.csv", csv_content.encode("utf-8"), content_type="text/csv")

        c = Client()
        c.force_login(user)
        r = c.post(reverse("import_members_upload"), {"csv_file": csv_file})

        if r.status_code == 200:
            content = r.content.decode("utf-8")
            # Vérifier que 3 utilisateurs ont été créés
            count = User.objects.filter(
                organization=org,
                email__startswith="__test_a1_",
            ).count()
            if count == 3:
                ok(f"3 utilisateurs créés en DB ✓")
            else:
                ko(f"Attendu 3 users, trouvé {count}")

            # Vérifier que l'HTML affiche les 3 emails
            if "__test_a1_1@test.local" in content:
                ok("Email 1 présent dans le résultat")
            if "MAT" in content or "TESTA1_001" in content:
                ok("Matricule présent dans le résultat")
        else:
            ko(f"Import → {r.status_code}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        ko(f"Erreur import : {e}")
    finally:
        # Nettoyage
        User.objects.filter(email__startswith="__test_a1_").delete()
        info("Utilisateurs de test nettoyés")

    # 7.4 Fichier non-CSV rejeté
    h2("7.4 Fichier non-CSV → rejeté")
    try:
        from django.core.files.uploadedfile import SimpleUploadedFile
        bad_file = SimpleUploadedFile("test.txt", b"not csv", content_type="text/plain")

        c = Client()
        c.force_login(user)
        r = c.post(reverse("import_members_upload"), {"csv_file": bad_file})

        if r.status_code == 200:
            content = r.content.decode("utf-8")
            if "csv" in content.lower() and ("doit" in content or "requis" in content):
                ok("Fichier non-CSV rejeté proprement")
            else:
                warn("Fichier non-CSV accepté (devrait être rejeté)")
        else:
            ko(f"Attendu 200, obtenu {r.status_code}")
    except Exception as e:
        ko(f"Erreur test non-CSV : {e}")

# ═══════════════════════════════════════════════════════════════
# TEST 8 — FONCTIONNEL : Envoi Email
# ═══════════════════════════════════════════════════════════════
h1("TEST 8 — FONCTIONNEL : EMAIL")

h2("8.1 Service send_email direct")
try:
    from django.test.utils import override_settings
    from apps.notifications.email_service import send_email

    with override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
        mail.outbox = []
        result = send_email(
            recipient_email="test@example.com",
            subject="Test ZionPay",
            template_name="emails/order_validated.html",
            context={
                "organization": user.organization,
                "order_number": "TEST-A1-0001",
                "total_amount": "45 000",
                "currency": "XOF",
                "order_url": "http://localhost/test",
                "color_primary": "#2563eb",
                "color_secondary": "#1e40af",
            },
        )
        if result is True:
            ok("send_email() retourne True")
        else:
            ko("send_email() retourne False")

        if len(mail.outbox) == 1:
            ok(f"1 email dans outbox")
            msg = mail.outbox[0]
            if msg.to == ["test@example.com"]:
                ok(f"Destinataire correct : {msg.to}")
            if "ZionPay" in msg.subject or "Commande" in msg.subject:
                ok(f"Sujet : {msg.subject}")
            # Vérifier le HTML
            html_alt = msg.alternatives
            if html_alt and "text/html" in html_alt[0][1]:
                ok("Alternative HTML présente")
            else:
                warn("Pas d'alternative HTML")
        else:
            ko(f"Attendu 1 email, trouvé {len(mail.outbox)}")
except Exception as e:
    import traceback
    traceback.print_exc()
    ko(f"Erreur test email : {e}")

h2("8.2 Envoi via send_order_validated_email")
try:
    from django.test.utils import override_settings
    from apps.notifications.email_service import send_order_validated_email
    from apps.orders.models import Order

    order = Order.objects.filter(organization=user.organization).first()
    if order:
        with override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            mail.outbox = []
            result = send_order_validated_email(order)
            if result and len(mail.outbox) == 1:
                ok(f"Email envoyé pour commande {order.order_number}")
                ok(f"To: {mail.outbox[0].to}")
            else:
                ko(f"Email non envoyé (result={result}, outbox={len(mail.outbox)})")
    else:
        warn("Aucune commande pour tester")
except Exception as e:
    ko(f"Erreur : {e}")

# ═══════════════════════════════════════════════════════════════
# TEST 9 — Navbar
# ═══════════════════════════════════════════════════════════════
h1("TEST 9 — NAVBAR")

h2("9.1 Lien 'Importer des membres'")
p = ROOT / "templates/components/navbar.html"
if p.exists():
    src = p.read_text(encoding="utf-8")
    if "url 'import_members'" in src:
        ok("Lien 'Importer des membres' présent dans navbar")
    else:
        ko("Lien 'Importer des membres' MANQUANT")

# ═══════════════════════════════════════════════════════════════
# TEST 10 — Cohérence globale
# ═══════════════════════════════════════════════════════════════
h1("TEST 10 — COHÉRENCE")

h2("10.1 Django check")
try:
    from django.core.management import call_command
    from io import StringIO
    out = StringIO()
    call_command("check", stdout=out, stderr=out)
    ok("Django check : OK")
except Exception as e:
    ko(f"check échoue : {e}")

h2("10.2 Migrations en attente")
try:
    from django.core.management import call_command
    from io import StringIO
    out = StringIO()
    try:
        call_command("makemigrations", "--check", "--dry-run", stdout=out, stderr=out)
        ok("Aucune migration en attente")
    except SystemExit:
        warn("Migrations en attente")
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
    print("  🎉 PACK A1 — TOUS LES TESTS PASSENT")
    print("  Import CSV + Emails HTML opérationnels")
elif results["failed"] <= 2:
    print("  ⚠️  PACK A1 — Quelques échecs mineurs")
else:
    print("  ❌ PACK A1 — Plusieurs échecs")

if results["failed"] > 0 or results["warned"] > 0:
    print()
    print("  📋 Détails des problèmes :")
    for status, msg in results["details"]:
        if status in ("FAIL", "WARN"):
            icon = "❌" if status == "FAIL" else "⚠️"
            print(f"     {icon} {msg}")

print()
print("═" * 70)
