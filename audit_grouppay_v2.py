python << 'PYEOF'
from pathlib import Path

content = '''"""Audit GroupPay v2.0 — Vérification complète contre le PRD v2.0."""
import os, sys, ast
from pathlib import Path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
try:
    import django
    django.setup()
except Exception as e:
    print("Django error:", e); sys.exit(1)

from django.apps import apps
from django.conf import settings
from django.urls import reverse, NoReverseMatch
import uuid

# ═══════════════════════════════════════════════════════════════
# Scan AST (rapide, sans venv)
# ═══════════════════════════════════════════════════════════════
FUNCS = set()
FILES = set()
EXCLUDE = {"venv", ".venv", "__pycache__", "migrations", ".git", ".kilo",
           "node_modules", "staticfiles", ".pytest_cache"}

for p in Path(".").rglob("*.py"):
    if set(p.parts) & EXCLUDE: continue
    if "audit_grouppay" in str(p): continue
    FILES.add(str(p))
    try:
        for n in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                FUNCS.add(n.name)
    except Exception:
        pass

has = lambda n: n in FUNCS

def h1(t):
    print("\\n" + "=" * 72)
    print("  " + t)
    print("=" * 72)

def h2(t):
    print("\\n> " + t)

results = {"passed": 0, "failed": 0, "warned": 0, "details": [], "sections": {}}

def ok(m, section=None):
    results["passed"] += 1
    results["details"].append(("PASS", m))
    if section: results["sections"].setdefault(section, {"p":0,"f":0,"w":0})["p"] += 1
    print("  OK  " + m)

def ko(m, section=None):
    results["failed"] += 1
    results["details"].append(("FAIL", m))
    if section: results["sections"].setdefault(section, {"p":0,"f":0,"w":0})["f"] += 1
    print("  XX  " + m)

def warn(m, section=None):
    results["warned"] += 1
    results["details"].append(("WARN", m))
    if section: results["sections"].setdefault(section, {"p":0,"f":0,"w":0})["w"] += 1
    print("  !!  " + m)

print("\\n" + "╔" + "═" * 70 + "╗")
print("║" + " AUDIT GROUPPAY v2.0 - Verification PRD v2.0 ".center(70) + "║")
print("╚" + "═" * 70 + "╝")

# ═══════════════════════════════════════════════════════════════
# SECTION 1 — MODELES (24 attendus)
# ═══════════════════════════════════════════════════════════════
h1("SECTION 1 — MODELES (24 attendus)")

MODELS = [
    # v1.0 (16)
    ("organizations", "Organization", "v1"),
    ("accounts", "User", "v1"),
    ("catalog", "Category", "v1"),
    ("catalog", "Product", "v1"),
    ("catalog", "ProductVariant", "v1"),
    ("orders", "Cart", "v1"),
    ("orders", "CartItem", "v1"),
    ("orders", "Order", "v1"),
    ("orders", "OrderItem", "v1"),
    ("orders", "OrderStatusHistory", "v1"),
    ("deductions", "DeductionTransmission", "v1"),
    ("deductions", "DeductionExportBatch", "v1"),
    ("deliveries", "Delivery", "v1"),
    ("deliveries", "DeliveryNoteDocument", "v1"),
    ("documents", "PurchaseOrderDocument", "v1"),
    ("notifications", "Notification", "v1"),
    # v2.0 (8)
    ("catalog", "Coupon", "v2"),
    ("catalog", "WishlistItem", "v2"),
    ("catalog", "Review", "v2"),
    ("catalog", "StockMovement", "v2"),
    ("catalog", "StockAlert", "v2"),
    ("catalog", "ProductRequest", "v2"),
    ("catalog", "ProductRequestVote", "v2"),
    ("documents", "InvoiceDocument", "v2"),
    # Optionnels
    ("audit", "AuditLog", "v1"),
]

models_ok = 0
for app_label, name, version in MODELS:
    try:
        m = apps.get_model(app_label, name)
        ok(f"{app_label}.{name} ({version})", "MODELES")
        models_ok += 1
    except LookupError:
        if version == "v2":
            ko(f"{app_label}.{name} MANQUANT (v2.0)", "MODELES")
        else:
            warn(f"{app_label}.{name} MANQUANT ({version})", "MODELES")

print(f"\\n  → {models_ok}/{len(MODELS)} modeles presents")

# ═══════════════════════════════════════════════════════════════
# SECTION 2 — REGLES METIER (RG-01 → RG-45)
# ═══════════════════════════════════════════════════════════════
h1("SECTION 2 — REGLES METIER (RG-01 → RG-45)")

RG = {
    # v1.0
    "RG-01": (["create_order_from_cart"], "Verrou stock anti-survente"),
    "RG-02": (["create_order_from_cart"], "Prix fige"),
    "RG-03": (["validate_order"], "Validation + Deduction"),
    "RG-04": (["reject_order"], "Refus restaure stock"),
    "RG-05": (["TenantModel"], "Isolation multi-tenant"),
    "RG-06": (["IsRH", "IsAdmin", "IsRHOrAdmin"], "Permissions RH/Admin"),
    "RG-07": (["reject_order"], "Refus avant livraison"),
    "RG-08": (["check_max_per_member"], "Max par membre"),
    "RG-09": (["cleanup_expired_carts"], "Panier expire 30j"),
    "RG-10": (["validate_order"], "Non modifiable apres validation"),
    "RG-11": (["expires_at"], "Deduction expire 30j"),
    "RG-12": (["generate_export_batch"], "Export CSV EN_ATTENTE -> ENVOYEE"),
    "RG-13": (["generate_purchase_order_pdf"], "PDF bon de commande"),
    "RG-14": (["generate_export_batch"], "CSV format fixe"),
    "RG-15": (["confirm_deduction", "deduction_webhook"], "Double confirmation webhook"),
    "RG-16": (["create_delivery_for_order"], "Livraison auto"),
    "RG-17": (["assign_courier"], "Assignation livreur"),
    "RG-18": (["mark_delivered"], "Preuve livraison"),
    "RG-19": (["mark_delivered"], "LIVREE cloture order"),
    "RG-20": (["attempt_delivery"], "Retry livraison max 3"),
    "RG-21": (["check_low_stock"], "Alerte stock critique"),
    "RG-22": (["CheckConstraint"], "Stock negatif interdit"),
    "RG-23": (["decrement_stock", "ProductVariant"], "Variant stock"),
    # v2.0 - Avis
    "RG-24": (["submit_review"], "Avis acheteurs verifies"),
    "RG-25": (["unique_review_per_member_product"], "1 avis par membre/produit"),
    "RG-26": (["submit_review"], "Rating 1-5"),
    "RG-27": (["is_published"], "Avis moderables"),
    "RG-28": (["average_rating"], "Moyenne sur avis publies"),
    "RG-29": (["delete_review"], "Suppression propre avis"),
    "RG-30": (["is_verified_purchase"], "Badge achat verifie"),
    # v2.0 - Stock avance
    "RG-31": (["StockMovement"], "Mouvement OUT"),
    "RG-32": (["StockMovement"], "Mouvement RESTORE"),
    "RG-33": (["adjust_stock"], "Mouvement ADJUST"),
    "RG-34": (["StockAlert"], "Creation alerte seuil"),
    "RG-35": (["StockAlert"], "Resolution alerte"),
    # v2.0 - Multi-fournisseurs
    "RG-36": (["supplier"], "Rattachement fournisseur"),
    "RG-37": (["my_products"], "Isolation produits fournisseur"),
    "RG-38": (["_is_owner"], "Modification propres produits"),
    "RG-39": (["suppliers_overview"], "Vue RH globale"),
    "RG-40": (["is_supplier_private"], "Produit prive brouillon"),
    # v2.0 - Wishlist collab
    "RG-41": (["request_create"], "Proposition produit"),
    "RG-42": (["request_create"], "Auto-vote auteur"),
    "RG-43": (["unique_vote_per_member_request"], "1 vote par membre"),
    "RG-44": (["vote_request"], "Vote toggle"),
    "RG-45": (["update_request_status"], "RH change statut"),
}

rg_ok = 0
for rg, (proofs, desc) in RG.items():
    found = [p for p in proofs if has(p)]
    # Cas special RG-22 : chercher dans les fichiers
    if rg == "RG-22" and not found:
        for f in FILES:
            if "catalog/models" in f:
                try:
                    if "CheckConstraint" in Path(f).read_text(errors="ignore"):
                        found = ["CheckConstraint"]
                        break
                except: pass
    if found:
        ok(f"{rg} : {desc}", "RG")
        rg_ok += 1
    else:
        ko(f"{rg} : {desc} — MANQUANT", "RG")

print(f"\\n  → {rg_ok}/{len(RG)} regles metier")

# ═══════════════════════════════════════════════════════════════
# SECTION 3 — PACK A (RH Essentials)
# ═══════════════════════════════════════════════════════════════
h1("SECTION 3 — PACK A : RH ESSENTIALS")

# A1 — Import CSV
h2("A1. Import CSV membres")
pack_a1 = [
    ("def import_members_page", "Vue page import"),
    ("def import_members_csv", "Vue traitement CSV"),
    ("def import_members_template", "Template CSV download"),
    ("import_members", "URL import"),
]
a1_ok = 0
for fn, desc in pack_a1:
    if has(fn) or any(fn in str(f) for f in FILES if "urls" in f):
        ok(desc, "PACK_A")
        a1_ok += 1
    else:
        ko(desc + " — MANQUANT", "PACK_A")

# A2 — Emails
h2("A2. Emails HTML")
pack_a2e = [
    ("send_email", "Service envoi"),
    ("send_order_validated_email", "Email validee"),
    ("send_order_delivered_email", "Email livree"),
    ("send_order_rejected_email", "Email refusee"),
    ("send_order_shipping_email", "Email en livraison"),
]
for fn, desc in pack_a2e:
    if has(fn):
        ok(desc, "PACK_A")
    else:
        ko(desc + " — MANQUANT", "PACK_A")

for tpl in ["order_validated", "order_delivered", "order_rejected", "order_shipping"]:
    p = Path(f"templates/emails/{tpl}.html")
    if p.exists():
        ok(f"Template email/{tpl}.html", "PACK_A")
    else:
        ko(f"Template email/{tpl}.html MANQUANT", "PACK_A")

# A3 — SMS
h2("A3. SMS")
pack_a3 = [
    ("send_sms", "Service SMS"),
    ("send_order_validated_sms", "SMS validee"),
    ("send_order_delivered_sms", "SMS livree"),
    ("send_order_rejected_sms", "SMS refusee"),
]
for fn, desc in pack_a3:
    if has(fn):
        ok(desc, "PACK_A")
    else:
        ko(desc + " — MANQUANT", "PACK_A")

# A4 — Factures PDF
h2("A4. Factures PDF")
pack_a4 = [
    ("generate_invoice_number", "Numerotation factures"),
    ("generate_invoice_pdf", "Generation PDF"),
    ("get_or_create_invoice", "Helper facture"),
    ("preview_invoice_html", "Preview HTML"),
    ("download_invoice_pdf", "Download PDF"),
]
for fn, desc in pack_a4:
    if has(fn):
        ok(desc, "PACK_A")
    else:
        ko(desc + " — MANQUANT", "PACK_A")

# A5 — Retenue UI
h2("A5. Dashboard retenue")
pack_a5 = [
    ("deductions_dashboard", "Dashboard retenue"),
    ("preview_export", "Apercu CSV"),
    ("generate_export", "Generation CSV"),
    ("download_batch", "Download batch"),
]
for fn, desc in pack_a5:
    if has(fn):
        ok(desc, "PACK_A")
    else:
        ko(desc + " — MANQUANT", "PACK_A")

# A6 — Fournisseur
h2("A6. Espace fournisseur")
if has("supplier_dashboard"):
    ok("Dashboard fournisseur", "PACK_A")
else:
    ko("Dashboard fournisseur MANQUANT", "PACK_A")

# ═══════════════════════════════════════════════════════════════
# SECTION 4 — PACK B (Marketplace)
# ═══════════════════════════════════════════════════════════════
h1("SECTION 4 — PACK B : MARKETPLACE")

# B1 — Avis
h2("B1. Avis produits")
b1 = ["product_reviews", "submit_review", "delete_review"]
for fn in b1:
    if has(fn):
        ok(fn + " present", "PACK_B")
    else:
        ko(fn + " MANQUANT", "PACK_B")

# B2 — Stock
h2("B2. Stock avance")
b2 = ["stock_dashboard", "product_stock_history", "adjust_stock", "resolve_alert",
      "decrement_stock", "increment_stock", "check_low_stock"]
for fn in b2:
    if has(fn):
        ok(fn + " present", "PACK_B")
    else:
        ko(fn + " MANQUANT", "PACK_B")

# B3 — Multi-fournisseurs
h2("B3. Multi-fournisseurs")
b3 = ["my_products", "product_form", "toggle_product_active", "delete_product", "suppliers_overview"]
for fn in b3:
    if has(fn):
        ok(fn + " present", "PACK_B")
    else:
        ko(fn + " MANQUANT", "PACK_B")

# B4 — Wishlist collab
h2("B4. Wishlist collaborative")
b4 = ["requests_list", "request_create", "vote_request", "delete_request", "update_request_status"]
for fn in b4:
    if has(fn):
        ok(fn + " present", "PACK_B")
    else:
        ko(fn + " MANQUANT", "PACK_B")

# ═══════════════════════════════════════════════════════════════
# SECTION 5 — PACK C (Professional)
# ═══════════════════════════════════════════════════════════════
h1("SECTION 5 — PACK C : PROFESSIONAL")

# C1 — 2FA
h2("C1. 2FA TOTP")
if "django_otp" in settings.INSTALLED_APPS:
    ok("django_otp dans INSTALLED_APPS", "PACK_C")
else:
    ko("django_otp MANQUANT", "PACK_C")

if "django_otp.plugins.otp_totp" in settings.INSTALLED_APPS:
    ok("otp_totp dans INSTALLED_APPS", "PACK_C")
else:
    ko("otp_totp MANQUANT", "PACK_C")

if any("django_otp" in m for m in settings.MIDDLEWARE):
    ok("OTPMiddleware", "PACK_C")
else:
    ko("OTPMiddleware MANQUANT", "PACK_C")

for fn in ["two_factor_setup", "two_factor_verify", "two_factor_disable", "two_factor_status"]:
    if has(fn):
        ok(fn + " present", "PACK_C")
    else:
        ko(fn + " MANQUANT", "PACK_C")

# C2 — Animations
h2("C2. Animations")
p = Path("templates/base.html")
if p.exists():
    src = p.read_text(encoding="utf-8")
    for needle, desc in [
        ("gpFadeIn", "Fade-in keyframe"),
        ("gp-stagger", "Stagger class"),
        ("gp-skeleton", "Skeleton loader"),
        ("gp-spinner", "Spinner"),
        ("prefers-reduced-motion", "Accessibility"),
    ]:
        if needle in src:
            ok(desc, "PACK_C")
        else:
            ko(desc + " MANQUANT", "PACK_C")

# C3 — PWA Install
h2("C3. PWA Install prompt")
if p.exists():
    for needle, desc in [
        ("gp-pwa-banner", "Bandeau install"),
        ("beforeinstallprompt", "Listener install"),
        ("gp-pwa-install", "Bouton installer"),
        ("appinstalled", "Event install"),
    ]:
        if needle in src:
            ok(desc, "PACK_C")
        else:
            ko(desc + " MANQUANT", "PACK_C")

# C4 — Sentry
h2("C4. Sentry")
for var in ["SENTRY_DSN", "SENTRY_ENVIRONMENT"]:
    if hasattr(settings, var):
        ok(var + " configure", "PACK_C")
    else:
        warn(var + " absent (opt-in)", "PACK_C")

if has("health"):
    ok("Endpoint /health/", "PACK_C")
else:
    ko("/health/ MANQUANT", "PACK_C")

# C5 — Tests E2E
h2("C5. Tests E2E")
e2e_files = list(Path("tests/e2e").rglob("*.py")) if Path("tests/e2e").exists() else []
if e2e_files:
    ok(f"{len(e2e_files)} fichiers E2E", "PACK_C")
else:
    ko("Aucun test E2E", "PACK_C")

# ═══════════════════════════════════════════════════════════════
# SECTION 6 — TESTS UNITAIRES
# ═══════════════════════════════════════════════════════════════
h1("SECTION 6 — TESTS UNITAIRES")

TESTS = [
    "test_order_creation_decreases_stock",
    "test_order_creation_fails_if_stock_insufficient",
    "test_unit_price_frozen_after_product_price_change",
    "test_validate_order_creates_deduction_transmission",
    "test_reject_order_restores_stock",
    "test_cannot_validate_already_validated_order",
    "test_export_batch_creates_csv_and_updates_status",
    "test_export_returns_none_when_nothing_pending",
    "test_users_are_isolated_by_organization",
    "test_same_email_allowed_across_different_organizations",
    "test_delivery_created_on_validation",
    "test_delivery_retry_limit_3",
    "test_delivered_closes_order",
    "test_low_stock_alert_triggered",
    "test_negative_stock_forbidden",
]
t_ok = 0
for t in TESTS:
    if has(t):
        ok(t, "TESTS")
        t_ok += 1
    else:
        warn(t + " manquant", "TESTS")
print(f"\\n  → {t_ok}/{len(TESTS)} tests")

# ═══════════════════════════════════════════════════════════════
# SECTION 7 — URLs
# ═══════════════════════════════════════════════════════════════
h1("SECTION 7 — URLs / ROUTES")

fake_id = uuid.uuid4()
URLS = [
    ("catalog", None),
    ("product_detail", "product_id"),
    ("view_cart", None),
    ("add_to_cart", "product_id"),
    ("remove_from_cart", "item_id"),
    ("update_cart_item_qty", "item_id"),
    ("apply_coupon", None),
    ("remove_coupon", None),
    ("create_order", None),
    ("my_orders", None),
    ("order_detail", "order_id"),
    ("download_pdf", "order_id"),
    ("preview_pdf", "order_id"),
    ("preview_order_html", "order_id"),
    ("preview_invoice_html", "order_id"),
    ("download_invoice_pdf", "order_id"),
    ("profile", None),
    ("save_theme", None),
    ("wishlist", None),
    ("toggle_wishlist", "product_id"),
    ("requests_list", None),
    ("request_create", None),
    ("vote_request", "request_id"),
    ("rh_dashboard", None),
    ("bulk_validate", None),
    ("bulk_reject", None),
    ("export_dashboard_excel", None),
    ("export_dashboard_pdf", None),
    ("deductions_dashboard", None),
    ("preview_export", None),
    ("generate_export", None),
    ("stock_dashboard", None),
    ("stock_history", "product_id"),
    ("adjust_stock", "product_id"),
    ("resolve_alert", "alert_id"),
    ("supplier_dashboard", None),
    ("supplier_my_products", None),
    ("supplier_product_new", None),
    ("suppliers_overview", None),
    ("import_members", None),
    ("import_members_upload", None),
    ("import_members_template", None),
    ("product_reviews", "product_id"),
    ("submit_review", "product_id"),
    ("two_factor_setup", None),
    ("two_factor_verify", None),
    ("two_factor_disable", None),
    ("two_factor_status", None),
    ("notif_unread_count", None),
    ("notif_list", None),
    ("health_check", None),
]

urls_ok = 0
for name, arg in URLS:
    try:
        if arg: reverse(name, kwargs={arg: fake_id})
        else: reverse(name)
        urls_ok += 1
    except NoReverseMatch:
        ko(f"URL '{name}' NON TROUVEE", "URLS")
    except Exception as e:
        warn(f"URL '{name}' : {e}", "URLS")
print(f"\\n  → {urls_ok}/{len(URLS)} URLs resolues")

# ═══════════════════════════════════════════════════════════════
# SECTION 8 — TEMPLATES
# ═══════════════════════════════════════════════════════════════
h1("SECTION 8 — TEMPLATES")

TEMPLATES = [
    "templates/base.html",
    "templates/components/navbar.html",
    "templates/components/footer.html",
    "templates/components/product_card.html",
    "templates/catalog/catalog.html",
    "templates/catalog/reviews.html",
    "templates/catalog/_stars.html",
    "templates/catalog/stock_dashboard.html",
    "templates/catalog/stock_history.html",
    "templates/catalog/supplier_products.html",
    "templates/catalog/supplier_product_form.html",
    "templates/catalog/suppliers_overview.html",
    "templates/catalog/supplier_dashboard.html",
    "templates/catalog/requests_list.html",
    "templates/catalog/request_form.html",
    "templates/orders/cart.html",
    "templates/orders/cart_badge.html",
    "templates/orders/my_orders.html",
    "templates/orders/order_detail.html",
    "templates/accounts/profile.html",
    "templates/accounts/wishlist.html",
    "templates/accounts/2fa_setup.html",
    "templates/accounts/2fa_enabled.html",
    "templates/admin/dashboard.html",
    "templates/admin/dashboard_pdf.html",
    "templates/admin/import_members.html",
    "templates/documents/invoice.html",
    "templates/documents/invoice_pdf.html",
    "templates/documents/preview.html",
    "templates/deductions/dashboard.html",
    "templates/deductions/_preview.html",
    "templates/emails/order_validated.html",
    "templates/emails/order_delivered.html",
    "templates/emails/order_rejected.html",
    "templates/emails/order_shipping.html",
]

tpl_ok = 0
for t in TEMPLATES:
    if Path(t).exists():
        tpl_ok += 1
    else:
        ko(f"{t} MANQUANT", "TEMPLATES")
print(f"\\n  → {tpl_ok}/{len(TEMPLATES)} templates")

# ═══════════════════════════════════════════════════════════════
# SECTION 9 — SETTINGS & INFRA
# ═══════════════════════════════════════════════════════════════
h1("SECTION 9 — SETTINGS & INFRA")

# Settings
settings_checks = [
    ("SESSION_ENGINE cached_db", hasattr(settings, "SESSION_ENGINE") and "cached_db" in settings.SESSION_ENGINE),
    ("CACHES configure", hasattr(settings, "CACHES")),
    ("REST_FRAMEWORK", hasattr(settings, "REST_FRAMEWORK")),
    ("OTP_TOTP_ISSUER", hasattr(settings, "OTP_TOTP_ISSUER")),
    ("SITE_URL", hasattr(settings, "SITE_URL")),
    ("AFRICASTALKING_USERNAME", hasattr(settings, "AFRICASTALKING_USERNAME")),
]
for desc, val in settings_checks:
    if val:
        ok(desc, "INFRA")
    else:
        ko(desc + " MANQUANT", "INFRA")

# Infrastructure files
infra_files = [
    "Dockerfile",
    "docker-compose.yml",
    ".github/workflows/ci.yml",
    "pytest.ini",
    "requirements.txt",
    "config/celery.py",
    "config/asgi.py",
]
for f in infra_files:
    if Path(f).exists():
        ok(f, "INFRA")
    else:
        ko(f + " MANQUANT", "INFRA")

# Static / PWA
for f in ["static/manifest.webmanifest", "static/sw.js",
          "static/img/icon-192.svg", "static/img/icon-512.svg"]:
    if Path(f).exists():
        ok(f, "INFRA")
    else:
        ko(f + " MANQUANT", "INFRA")

# ═══════════════════════════════════════════════════════════════
# SECTION 10 — APPS & SERVICES
# ═══════════════════════════════════════════════════════════════
h1("SECTION 10 — SERVICES METIER")

SERVICES = [
    "apps/orders/services.py",
    "apps/catalog/services.py",
    "apps/catalog/review_views.py",
    "apps/catalog/stock_views.py",
    "apps/catalog/supplier_views.py",
    "apps/catalog/supplier_product_views.py",
    "apps/catalog/request_views.py",
    "apps/deductions/services.py",
    "apps/deductions/views.py",
    "apps/deductions/webhooks.py",
    "apps/deductions/tasks.py",
    "apps/deliveries/services.py",
    "apps/documents/services.py",
    "apps/documents/views.py",
    "apps/documents/invoice_service.py",
    "apps/notifications/email_service.py",
    "apps/notifications/sms_service.py",
    "apps/notifications/signals.py",
    "apps/notifications/consumers.py",
    "apps/notifications/routing.py",
    "apps/audit/models.py",
    "apps/audit/middleware.py",
    "apps/accounts/permissions.py",
    "apps/accounts/two_factor_views.py",
    "apps/accounts/views.py",
    "apps/orders/dashboard_views.py",
    "apps/orders/export_views.py",
    "apps/orders/tasks.py",
    "apps/orders/context_processors.py",
]

svc_ok = 0
for s in SERVICES:
    if Path(s).exists():
        svc_ok += 1
    else:
        ko(f"{s} MANQUANT", "SERVICES")
print(f"\\n  → {svc_ok}/{len(SERVICES)} services")

# ═══════════════════════════════════════════════════════════════
# SCORE FINAL
# ═══════════════════════════════════════════════════════════════
h1("SCORE FINAL — CONFORMITE PRD v2.0")

# Calcul du score pondere
score_models = models_ok / len(MODELS)
score_rg = rg_ok / len(RG)
score_tests = t_ok / len(TESTS) if TESTS else 0
score_urls = urls_ok / len(URLS)
score_tpl = tpl_ok / len(TEMPLATES)
score_svc = svc_ok / len(SERVICES)

global_score = (
    score_models * 0.20 +
    score_rg * 0.30 +
    score_urls * 0.15 +
    score_tpl * 0.15 +
    score_svc * 0.10 +
    score_tests * 0.10
) * 100

print()
print(f"  Modeles      : {models_ok}/{len(MODELS)}  ({score_models*100:.1f}%)")
print(f"  Regles       : {rg_ok}/{len(RG)}  ({score_rg*100:.1f}%)")
print(f"  Tests        : {t_ok}/{len(TESTS)}  ({score_tests*100:.1f}%)")
print(f"  URLs         : {urls_ok}/{len(URLS)}  ({score_urls*100:.1f}%)")
print(f"  Templates    : {tpl_ok}/{len(TEMPLATES)}  ({score_tpl*100:.1f}%)")
print(f"  Services     : {svc_ok}/{len(SERVICES)}  ({score_svc*100:.1f}%)")
print()
print("  " + "=" * 60)
print(f"  SCORE GLOBAL : {global_score:.1f}%")
print("  " + "=" * 60)

# Résumé par PACK
h1("RESUME PAR PACK")

for pack in ["PACK_A", "PACK_B", "PACK_C"]:
    s = results["sections"].get(pack, {"p": 0, "f": 0, "w": 0})
    total = s["p"] + s["f"] + s["w"]
    pct = (s["p"] / total * 100) if total > 0 else 0
    status = "OK" if s["f"] == 0 else "INCOMPLET"
    print(f"  {pack:<10} : {s['p']}/{total} ({pct:.0f}%) [{status}]")

# Verdict final
h1("VERDICT FINAL")

if global_score >= 95:
    print("  ✓ PLATEFORME CONFORME AU PRD v2.0")
    print("  → Pret pour deploiement en production")
elif global_score >= 85:
    print("  ~ QUELQUES AMELIORATIONS POSSIBLES")
    print("  → Corriger les manques ci-dessus")
elif global_score >= 70:
    print("  ! PLUSIEURS MANQUES")
    print("  → Completer les features manquantes")
else:
    print("  XX CONFORMITE INSUFFISANTE")
    print("  → Retravailler les fondations")

# Details des echecs
print()
if results["failed"] > 0:
    print("  DETAIL DES ECHECS :")
    for s, m in results["details"]:
        if s == "FAIL":
            print("     XX " + m)

print()
print("=" * 72)
print(f"  Total : {results['passed']} passes / {results['failed']} echecs / {results['warned']} warnings")
print("=" * 72)
print()
'''

Path("audit_grouppay_v2.py").write_text(content, encoding="utf-8")
print("OK audit_grouppay_v2.py cree (" + str(content.count(chr(10))) + " lignes)")
PYEOF

echo ""
echo "👉 Lance l'audit v2 (devrait prendre < 5 sec) :"
python audit_grouppay_v2.py