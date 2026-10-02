"""Test automatisé — Pack A2 : Factures PDF + Export retenue salariale UI."""
import os
import sys
from pathlib import Path
from datetime import date, timedelta

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

# ═══════════════════════════════════════════════════════════════
# Header
# ═══════════════════════════════════════════════════════════════
print()
print("╔" + "═" * 68 + "╗")
print("║" + "  TEST PACK A2 — Factures PDF + Export retenue".center(68) + "║")
print("║" + f"  {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}".center(68) + "║")
print("╚" + "═" * 68 + "╝")

# ═══════════════════════════════════════════════════════════════
# TEST 1 — Modèles
# ═══════════════════════════════════════════════════════════════
h1("TEST 1 — MODÈLES")

h2("1.1 InvoiceDocument")
try:
    Inv = apps.get_model("documents", "InvoiceDocument")
    fields = {f.name for f in Inv._meta.get_fields()}
    required = ["order", "invoice_number", "file", "file_hash",
                "generated_at", "downloaded_at", "download_count"]
    missing = [f for f in required if f not in fields]
    if missing:
        ko(f"InvoiceDocument manque : {missing}")
    else:
        ok(f"InvoiceDocument OK ({len(fields)} champs)")
except Exception as e:
    ko(f"InvoiceDocument inaccessible : {e}")

# ═══════════════════════════════════════════════════════════════
# TEST 2 — Fichiers sources
# ═══════════════════════════════════════════════════════════════
h1("TEST 2 — FICHIERS SOURCES")

files_to_check = {
    "apps/documents/invoice_service.py": [
        "def generate_invoice_number",
        "def generate_invoice_pdf",
        "def get_or_create_invoice",
    ],
    "apps/deductions/views.py": [
        "def deductions_dashboard",
        "def preview_export",
        "def generate_export",
        "def download_batch",
        "def mark_batch_sent",
    ],
    "apps/documents/views.py": [
        "def preview_invoice_html",
        "def preview_invoice_pdf",
        "def download_invoice_pdf",
    ],
}

for path, needles in files_to_check.items():
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
# TEST 3 — Templates
# ═══════════════════════════════════════════════════════════════
h1("TEST 3 — TEMPLATES")

templates_to_check = {
    "templates/documents/invoice.html": [
        "invoice_number", "TOTAL TTC", "Retenue salariale",
    ],
    "templates/documents/invoice_pdf.html": [
        "invoice_number", "TOTAL TTC",
    ],
    "templates/deductions/dashboard.html": [
        "previewPeriod", "period-start", "generate_export",
    ],
    "templates/deductions/_preview.html": [
        "internal_id", "TOTAL",
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
# TEST 4 — URLs
# ═══════════════════════════════════════════════════════════════
h1("TEST 4 — URLs")

urls_to_test = [
    ("preview_invoice_html", "order_id", "PREVIEW_INVOICE"),
    ("download_invoice_pdf", "order_id", "DOWNLOAD_INVOICE"),
    ("preview_invoice_pdf", "order_id", "PREVIEW_INVOICE_PDF"),
    ("deductions_dashboard", None, "DEDUCTIONS"),
    ("preview_export", None, "PREVIEW_EXPORT"),
    ("generate_export", None, "GENERATE_EXPORT"),
]

import uuid
fake_uuid = uuid.uuid4()

for name, arg, label in urls_to_test:
    try:
        if arg:
            url = reverse(name, kwargs={arg: fake_uuid})
        else:
            url = reverse(name)
        ok(f"{name} → {url}")
    except NoReverseMatch:
        ko(f"{name} → NON TROUVÉE")

# ═══════════════════════════════════════════════════════════════
# TEST 5 — Import des modules
# ═══════════════════════════════════════════════════════════════
h1("TEST 5 — IMPORTS")

h2("5.1 invoice_service")
try:
    from apps.documents.invoice_service import (
        generate_invoice_number, generate_invoice_pdf, get_or_create_invoice,
    )
    ok("invoice_service importable")
except Exception as e:
    ko(f"Import impossible : {e}")

h2("5.2 deductions.views")
try:
    from apps.deductions.views import (
        deductions_dashboard, preview_export, generate_export,
        download_batch, mark_batch_sent,
    )
    ok("deductions.views importable")
except Exception as e:
    ko(f"Import impossible : {e}")

# ═══════════════════════════════════════════════════════════════
# TEST 6 — FONCTIONNEL : Facture
# ═══════════════════════════════════════════════════════════════
h1("TEST 6 — FONCTIONNEL : FACTURE")

user = User.objects.filter(is_superuser=True).first()
if not user:
    ko("Aucun superuser")
else:
    info(f"User : {user.email}")
    from apps.orders.models import Order

    # 6.1 Génération numéro facture
    h2("6.1 generate_invoice_number")
    try:
        from apps.documents.invoice_service import generate_invoice_number
        order = Order.objects.filter(organization=user.organization).first()
        if order:
            num = generate_invoice_number(order)
            if num and num.startswith("FAC-"):
                ok(f"Numéro généré : {num}")
            else:
                ko(f"Format invalide : {num}")
        else:
            warn("Aucune commande pour tester")
    except Exception as e:
        ko(f"Erreur : {e}")

    # 6.2 Génération PDF
    h2("6.2 generate_invoice_pdf")
    try:
        from apps.documents.invoice_service import generate_invoice_pdf
        from apps.documents.models import InvoiceDocument

        # Nettoyer avant
        InvoiceDocument.objects.filter(order=order).delete()

        doc = generate_invoice_pdf(order)
        if doc and doc.file:
            size = doc.file.size
            ok(f"Facture générée : {doc.invoice_number} ({size} bytes)")
            ok(f"Hash SHA256 : {doc.file_hash[:16]}...")
        else:
            ko("Fichier non généré")
    except Exception as e:
        import traceback; traceback.print_exc()
        ko(f"Erreur : {e}")

    # 6.3 Page preview_invoice_html
    h2("6.3 GET /orders/<id>/invoice/")
    try:
        c = Client()
        c.force_login(user)
        url = reverse("preview_invoice_html", kwargs={"order_id": order.id})
        r = c.get(url)
        if r.status_code == 200:
            content = r.content.decode("utf-8")
            if "Facture" in content and "TOTAL TTC" in content:
                ok(f"Page facture → 200 ({len(content)} bytes)")
            else:
                warn("Page chargée mais contenu inattendu")
        else:
            ko(f"Page facture → {r.status_code}")
    except Exception as e:
        ko(f"Erreur : {e}")

    # 6.4 Download PDF
    h2("6.4 GET /orders/<id>/invoice/pdf/")
    try:
        c = Client()
        c.force_login(user)
        url = reverse("download_invoice_pdf", kwargs={"order_id": order.id})
        r = c.get(url)
        if r.status_code == 200:
            ct = r.get("Content-Type", "")
            cd = r.get("Content-Disposition", "")
            if "application/pdf" in ct or "attachment" in cd:
                ok(f"PDF download → 200 ({ct})")
            else:
                warn(f"Headers inattendus : CT={ct}, CD={cd}")
        else:
            ko(f"PDF download → {r.status_code}")
    except Exception as e:
        ko(f"Erreur : {e}")

    # 6.5 Preview PDF inline
    h2("6.5 GET /orders/<id>/invoice/pdf/preview/")
    try:
        c = Client()
        c.force_login(user)
        url = reverse("preview_invoice_pdf", kwargs={"order_id": order.id})
        r = c.get(url)
        if r.status_code == 200:
            ok(f"PDF preview → 200")
        else:
            ko(f"PDF preview → {r.status_code}")
    except Exception as e:
        ko(f"Erreur : {e}")

# ═══════════════════════════════════════════════════════════════
# TEST 7 — FONCTIONNEL : Retenue salariale
# ═══════════════════════════════════════════════════════════════
h1("TEST 7 — FONCTIONNEL : RETENUE")

if user:
    # 7.1 Dashboard
    h2("7.1 GET /rh/deductions/")
    try:
        c = Client()
        c.force_login(user)
        url = reverse("deductions_dashboard")
        r = c.get(url)
        if r.status_code == 200:
            content = r.content.decode("utf-8")
            if "Retenue salariale" in content and "previewPeriod" in content:
                ok(f"Dashboard retenue → 200 ({len(content)} bytes)")
            else:
                warn("Contenu inattendu")
        else:
            ko(f"Dashboard → {r.status_code}")
    except Exception as e:
        ko(f"Erreur : {e}")

    # 7.2 Aperçu période
    h2("7.2 GET /rh/deductions/preview/")
    try:
        c = Client()
        c.force_login(user)
        url = reverse("preview_export")
        today = date.today()
        start = (today - timedelta(days=90)).isoformat()
        end = today.isoformat()
        r = c.get(f"{url}?start={start}&end={end}")
        if r.status_code == 200:
            content = r.content.decode("utf-8")
            if "TOTAL" in content or "Aucune transmission" in content:
                ok(f"Aperçu → 200 ({len(content)} bytes)")
            else:
                warn("Contenu inattendu")
        else:
            ko(f"Aperçu → {r.status_code}")
    except Exception as e:
        ko(f"Erreur : {e}")

    # 7.3 Dates invalides
    h2("7.3 GET preview avec dates invalides")
    try:
        c = Client()
        c.force_login(user)
        url = reverse("preview_export")
        r = c.get(f"{url}?start=invalid&end=bad")
        if r.status_code == 400:
            ok("Dates invalides → 400 (correct)")
        else:
            warn(f"Attendu 400, obtenu {r.status_code}")
    except Exception as e:
        ko(f"Erreur : {e}")

# ═══════════════════════════════════════════════════════════════
# TEST 8 — Permissions
# ═══════════════════════════════════════════════════════════════
h1("TEST 8 — PERMISSIONS")

# Créer un membre normal pour tester
h2("8.1 Membre ne peut pas accéder à /rh/deductions/")
try:
    member = User.objects.filter(role="MEMBRE").first()
    if member:
        c = Client()
        c.force_login(member)
        url = reverse("deductions_dashboard")
        r = c.get(url)
        if r.status_code == 403:
            ok("Membre → 403 (correct)")
        elif r.status_code == 302:
            ok("Membre → redirigé (correct)")
        else:
            warn(f"Membre → {r.status_code} (attendu 403)")
    else:
        warn("Aucun membre pour tester")
except Exception as e:
    ko(f"Erreur : {e}")

# ═══════════════════════════════════════════════════════════════
# TEST 9 — Navbar + Boutons
# ═══════════════════════════════════════════════════════════════
h1("TEST 9 — UI")

h2("9.1 Bouton Facture dans order_detail")
p = ROOT / "templates/orders/order_detail.html"
if p.exists():
    src = p.read_text(encoding="utf-8")
    if "preview_invoice_html" in src:
        ok("Bouton Facture présent")
    else:
        ko("Bouton Facture MANQUANT")

h2("9.2 Lien Retenue salariale dans navbar")
p = ROOT / "templates/components/navbar.html"
if p.exists():
    src = p.read_text(encoding="utf-8")
    if "url 'deductions_dashboard'" in src:
        ok("Lien Retenue présent")
    else:
        ko("Lien Retenue MANQUANT")

# ═══════════════════════════════════════════════════════════════
# TEST 10 — Cohérence
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
    print("  🎉 PACK A2 — TOUS LES TESTS PASSENT")
    print("  Factures PDF + Retenue salariale opérationnels")
elif results["failed"] <= 2:
    print("  ⚠️  PACK A2 — Quelques échecs mineurs")
else:
    print("  ❌ PACK A2 — Plusieurs échecs")

if results["failed"] > 0 or results["warned"] > 0:
    print()
    print("  📋 Détails des problèmes :")
    for status, msg in results["details"]:
        if status in ("FAIL", "WARN"):
            icon = "❌" if status == "FAIL" else "⚠️"
            print(f"     {icon} {msg}")

print()
print("═" * 70)
