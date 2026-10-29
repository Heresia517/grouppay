"""Audit ZionPay v2.1 - Complet (fonctions + champs + contraintes)."""
import os, sys, ast
from pathlib import Path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
try:
    import django
    django.setup()
except Exception as e:
    print("Django error:", e)
    sys.exit(1)

from django.apps import apps
from django.conf import settings
from django.urls import reverse, NoReverseMatch
import uuid

# ═══════════════════════════════════════════════════════════════
# SCAN AST COMPLET — fonctions + champs + contraintes
# ═══════════════════════════════════════════════════════════════
FUNCS = set()
FIELDS = set()
CONSTRAINTS = set()
FILES = set()

EXCLUDE = {"venv", ".venv", "__pycache__", "migrations", ".git",
           ".kilo", "node_modules", "staticfiles", ".pytest_cache"}

for path in Path(".").rglob("*.py"):
    if set(path.parts) & EXCLUDE:
        continue
    if "audit_zionpay" in str(path):
        continue
    FILES.add(str(path))
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            # Fonctions et classes
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                FUNCS.add(node.name)
            # Champs de modele : name = models.XxxField(...)
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and isinstance(node.value, ast.Call):
                        func = node.value.func
                        if isinstance(func, ast.Attribute):
                            if "Field" in func.attr or func.attr == "ForeignKey" or func.attr == "OneToOneField":
                                FIELDS.add(target.id)
            # Contraintes : name="xxx"
            if isinstance(node, ast.keyword) and node.arg == "name":
                if isinstance(node.value, ast.Constant):
                    CONSTRAINTS.add(node.value.value)
    except Exception:
        pass

ALL_SYMBOLS = FUNCS | FIELDS | CONSTRAINTS
has = lambda n: n in ALL_SYMBOLS


def h1(title):
    print()
    print("=" * 72)
    print("  " + title)
    print("=" * 72)


def h2(title):
    print()
    print("> " + title)


results = {"passed": 0, "failed": 0, "warned": 0, "details": [], "sections": {}}


def ok(msg, section=None):
    results["passed"] += 1
    results["details"].append(("PASS", msg))
    if section:
        results["sections"].setdefault(section, {"p": 0, "f": 0, "w": 0})["p"] += 1
    print("  OK  " + msg)


def ko(msg, section=None):
    results["failed"] += 1
    results["details"].append(("FAIL", msg))
    if section:
        results["sections"].setdefault(section, {"p": 0, "f": 0, "w": 0})["f"] += 1
    print("  XX  " + msg)


def warn(msg, section=None):
    results["warned"] += 1
    results["details"].append(("WARN", msg))
    if section:
        results["sections"].setdefault(section, {"p": 0, "f": 0, "w": 0})["w"] += 1
    print("  !!  " + msg)


print()
print("=" * 72)
print("  AUDIT ZIONPAY v2.1 - Verification PRD v2.0".center(72))
print("=" * 72)

# ═══════════════════════════════════════════════════════════════
# SECTION 1 - MODELES
# ═══════════════════════════════════════════════════════════════
h1("SECTION 1 - MODELES (25 attendus)")

MODELS = [
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
    ("catalog", "Coupon", "v2"),
    ("catalog", "WishlistItem", "v2"),
    ("catalog", "Review", "v2"),
    ("catalog", "StockMovement", "v2"),
    ("catalog", "StockAlert", "v2"),
    ("catalog", "ProductRequest", "v2"),
    ("catalog", "ProductRequestVote", "v2"),
    ("documents", "InvoiceDocument", "v2"),
    ("audit", "AuditLog", "v1"),
]

models_ok = 0
for app_label, name, version in MODELS:
    try:
        apps.get_model(app_label, name)
        ok(app_label + "." + name + " (" + version + ")", "MODELES")
        models_ok += 1
    except LookupError:
        ko(app_label + "." + name + " MANQUANT", "MODELES")

print()
print("  -> " + str(models_ok) + "/" + str(len(MODELS)) + " modeles")

# ═══════════════════════════════════════════════════════════════
# SECTION 2 - REGLES METIER
# ═══════════════════════════════════════════════════════════════
h1("SECTION 2 - REGLES METIER (RG-01 -> RG-45)")

RG = {
    "RG-01": (["create_order_from_cart"], "Verrou stock"),
    "RG-02": (["create_order_from_cart"], "Prix fige"),
    "RG-03": (["validate_order"], "Validation + Deduction"),
    "RG-04": (["reject_order"], "Refus restaure stock"),
    "RG-05": (["TenantModel"], "Isolation multi-tenant"),
    "RG-06": (["IsRH", "IsAdmin", "IsRHOrAdmin"], "Permissions RH/Admin"),
    "RG-07": (["reject_order"], "Refus avant livraison"),
    "RG-08": (["check_max_per_member"], "Max par membre"),
    "RG-09": (["cleanup_expired_carts"], "Panier expire"),
    "RG-10": (["validate_order"], "Non modifiable"),
    "RG-11": (["expires_at"], "Deduction expire"),
    "RG-12": (["generate_export_batch"], "Export CSV"),
    "RG-13": (["generate_purchase_order_pdf"], "PDF BC"),
    "RG-14": (["generate_export_batch"], "CSV format"),
    "RG-15": (["confirm_deduction", "deduction_webhook"], "Webhook"),
    "RG-16": (["create_delivery_for_order"], "Livraison auto"),
    "RG-17": (["assign_courier"], "Assignation livreur"),
    "RG-18": (["mark_delivered"], "Preuve livraison"),
    "RG-19": (["mark_delivered"], "LIVREE cloture"),
    "RG-20": (["attempt_delivery"], "Retry livraison"),
    "RG-21": (["check_low_stock"], "Alerte stock"),
    "RG-22": (["CheckConstraint", "product_stock_non_negative"], "Stock negatif interdit"),
    "RG-23": (["decrement_stock", "ProductVariant"], "Variant stock"),
    "RG-24": (["submit_review"], "Avis acheteurs verifies"),
    "RG-25": (["unique_review_per_member_product"], "1 avis/membre/produit"),
    "RG-26": (["submit_review"], "Rating 1-5"),
    "RG-27": (["is_published"], "Avis moderables"),
    "RG-28": (["average_rating"], "Moyenne publies"),
    "RG-29": (["delete_review"], "Suppression avis"),
    "RG-30": (["is_verified_purchase"], "Badge verifie"),
    "RG-31": (["StockMovement"], "Mouvement OUT"),
    "RG-32": (["StockMovement"], "Mouvement RESTORE"),
    "RG-33": (["adjust_stock"], "Mouvement ADJUST"),
    "RG-34": (["StockAlert"], "Creation alerte"),
    "RG-35": (["StockAlert"], "Resolution alerte"),
    "RG-36": (["supplier"], "Rattachement fournisseur"),
    "RG-37": (["my_products"], "Isolation produits"),
    "RG-38": (["_is_owner"], "Modif propres produits"),
    "RG-39": (["suppliers_overview"], "Vue RH globale"),
    "RG-40": (["is_supplier_private"], "Produit prive"),
    "RG-41": (["request_create"], "Proposition produit"),
    "RG-42": (["request_create"], "Auto-vote auteur"),
    "RG-43": (["unique_vote_per_member_request"], "1 vote/membre"),
    "RG-44": (["vote_request"], "Vote toggle"),
    "RG-45": (["update_request_status"], "RH change statut"),
}

rg_ok = 0
for rg, (proofs, desc) in RG.items():
    found = [p for p in proofs if has(p)]
    if found:
        ok(rg + " : " + desc, "RG")
        rg_ok += 1
    else:
        ko(rg + " : " + desc, "RG")

print()
print("  -> " + str(rg_ok) + "/" + str(len(RG)) + " regles")

# ═══════════════════════════════════════════════════════════════
# SECTION 3 - PACK A
# ═══════════════════════════════════════════════════════════════
h1("SECTION 3 - PACK A : RH ESSENTIALS")

h2("A1. Import CSV")
for fn in ["import_members_page", "import_members_csv", "import_members_template"]:
    (ok if has(fn) else ko)(fn, "PACK_A")

h2("A2. Emails")
for fn in ["send_email", "send_order_validated_email", "send_order_delivered_email",
           "send_order_rejected_email", "send_order_shipping_email"]:
    (ok if has(fn) else ko)(fn, "PACK_A")

h2("A3. SMS")
for fn in ["send_sms", "send_order_validated_sms", "send_order_delivered_sms",
           "send_order_rejected_sms"]:
    (ok if has(fn) else ko)(fn, "PACK_A")

h2("A4. Factures PDF")
for fn in ["generate_invoice_number", "generate_invoice_pdf", "preview_invoice_html",
           "download_invoice_pdf", "get_or_create_invoice"]:
    (ok if has(fn) else ko)(fn, "PACK_A")

h2("A5. Retenue UI")
for fn in ["deductions_dashboard", "preview_export", "generate_export",
           "download_batch", "mark_batch_sent"]:
    (ok if has(fn) else ko)(fn, "PACK_A")

h2("A6. Fournisseur")
(ok if has("supplier_dashboard") else ko)("supplier_dashboard", "PACK_A")

# ═══════════════════════════════════════════════════════════════
# SECTION 4 - PACK B
# ═══════════════════════════════════════════════════════════════
h1("SECTION 4 - PACK B : MARKETPLACE")

h2("B1. Avis")
for fn in ["product_reviews", "submit_review", "delete_review"]:
    (ok if has(fn) else ko)(fn, "PACK_B")

h2("B2. Stock avance")
for fn in ["stock_dashboard", "product_stock_history", "adjust_stock", "resolve_alert",
           "decrement_stock", "increment_stock", "check_low_stock"]:
    (ok if has(fn) else ko)(fn, "PACK_B")

h2("B3. Multi-fournisseurs")
for fn in ["my_products", "product_form", "toggle_product_active", "delete_product",
           "suppliers_overview"]:
    (ok if has(fn) else ko)(fn, "PACK_B")

h2("B4. Wishlist collaborative")
for fn in ["requests_list", "request_create", "vote_request", "delete_request",
           "update_request_status"]:
    (ok if has(fn) else ko)(fn, "PACK_B")

# ═══════════════════════════════════════════════════════════════
# SECTION 5 - PACK C
# ═══════════════════════════════════════════════════════════════
h1("SECTION 5 - PACK C : PROFESSIONAL")

h2("C1. 2FA")
(ok if "django_otp" in settings.INSTALLED_APPS else ko)("django_otp", "PACK_C")
(ok if "django_otp.plugins.otp_totp" in settings.INSTALLED_APPS else ko)("otp_totp", "PACK_C")
(ok if any("django_otp" in m for m in settings.MIDDLEWARE) else ko)("OTPMiddleware", "PACK_C")
for fn in ["two_factor_setup", "two_factor_verify", "two_factor_disable", "two_factor_status"]:
    (ok if has(fn) else ko)(fn, "PACK_C")

h2("C2. Animations")
p = Path("templates/base.html")
if p.exists():
    src = p.read_text(encoding="utf-8")
    for needle, desc in [("gpFadeIn", "Fade-in"), ("gp-stagger", "Stagger"),
                         ("gp-skeleton", "Skeleton"), ("prefers-reduced-motion", "A11y")]:
        (ok if needle in src else ko)(desc, "PACK_C")

h2("C3. PWA")
if p.exists():
    for needle, desc in [("gp-pwa-banner", "Bandeau"), ("beforeinstallprompt", "Listener"),
                         ("gp-pwa-install", "Bouton")]:
        (ok if needle in src else ko)(desc, "PACK_C")

h2("C4. Monitoring")
(ok if has("health") else ko)("fonction health()", "PACK_C")
(ok if has("sentry_test") else ko)("fonction sentry_test()", "PACK_C")

h2("C5. Tests E2E")
e2e_dir = Path("tests/e2e")
if e2e_dir.exists() and list(e2e_dir.rglob("*.py")):
    (ok)(str(len(list(e2e_dir.rglob("*.py")))) + " fichiers E2E", "PACK_C")
else:
    ko("Tests E2E MANQUANTS", "PACK_C")

# ═══════════════════════════════════════════════════════════════
# SECTION 6 - TESTS UNITAIRES
# ═══════════════════════════════════════════════════════════════
h1("SECTION 6 - TESTS UNITAIRES")

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

print()
print("  -> " + str(t_ok) + "/" + str(len(TESTS)) + " tests")

# ═══════════════════════════════════════════════════════════════
# SECTION 7 - URLs
# ═══════════════════════════════════════════════════════════════
h1("SECTION 7 - URLs")

fake_id = uuid.uuid4()
URLS = [
    ("catalog", None), ("product_detail", "product_id"),
    ("view_cart", None), ("add_to_cart", "product_id"),
    ("remove_from_cart", "item_id"), ("update_cart_item_qty", "item_id"),
    ("apply_coupon", None), ("remove_coupon", None),
    ("create_order", None), ("my_orders", None),
    ("order_detail", "order_id"), ("download_pdf", "order_id"),
    ("preview_pdf", "order_id"), ("preview_order_html", "order_id"),
    ("preview_invoice_html", "order_id"), ("download_invoice_pdf", "order_id"),
    ("profile", None), ("save_theme", None),
    ("wishlist", None), ("toggle_wishlist", "product_id"),
    ("requests_list", None), ("request_create", None), ("vote_request", "request_id"),
    ("rh_dashboard", None), ("bulk_validate", None), ("bulk_reject", None),
    ("export_dashboard_excel", None), ("export_dashboard_pdf", None),
    ("deductions_dashboard", None), ("preview_export", None), ("generate_export", None),
    ("stock_dashboard", None), ("stock_history", "product_id"),
    ("adjust_stock", "product_id"), ("resolve_alert", "alert_id"),
    ("supplier_dashboard", None), ("supplier_my_products", None),
    ("supplier_product_new", None), ("suppliers_overview", None),
    ("import_members", None), ("import_members_upload", None),
    ("import_members_template", None),
    ("product_reviews", "product_id"), ("submit_review", "product_id"),
    ("two_factor_setup", None), ("two_factor_verify", None),
    ("two_factor_disable", None), ("two_factor_status", None),
    ("notif_unread_count", None), ("notif_list", None),
    ("health_check", None), ("sentry_test", None),
]

urls_ok = 0
for name, arg in URLS:
    try:
        if arg:
            reverse(name, kwargs={arg: fake_id})
        else:
            reverse(name)
        urls_ok += 1
    except NoReverseMatch:
        ko("URL '" + name + "' non trouvee", "URLS")

print()
print("  -> " + str(urls_ok) + "/" + str(len(URLS)) + " URLs")

# ═══════════════════════════════════════════════════════════════
# SECTION 8 - TEMPLATES
# ═══════════════════════════════════════════════════════════════
h1("SECTION 8 - TEMPLATES")

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
        ko(t + " MANQUANT", "TEMPLATES")

print()
print("  -> " + str(tpl_ok) + "/" + str(len(TEMPLATES)) + " templates")

# ═══════════════════════════════════════════════════════════════
# SECTION 9 - INFRA
# ═══════════════════════════════════════════════════════════════
h1("SECTION 9 - SETTINGS & INFRA")

for desc, val in [
    ("SESSION_ENGINE cached_db", hasattr(settings, "SESSION_ENGINE") and "cached_db" in settings.SESSION_ENGINE),
    ("CACHES", hasattr(settings, "CACHES")),
    ("REST_FRAMEWORK", hasattr(settings, "REST_FRAMEWORK")),
    ("OTP_TOTP_ISSUER", hasattr(settings, "OTP_TOTP_ISSUER")),
    ("SITE_URL", hasattr(settings, "SITE_URL")),
]:
    (ok if val else ko)(desc, "INFRA")

for f in ["Dockerfile", "docker-compose.yml", ".github/workflows/ci.yml",
          "pytest.ini", "requirements.txt", "config/celery.py", "config/asgi.py",
          "static/manifest.webmanifest", "static/sw.js"]:
    (ok if Path(f).exists() else ko)(f, "INFRA")

# ═══════════════════════════════════════════════════════════════
# SCORE FINAL
# ═══════════════════════════════════════════════════════════════
h1("SCORE FINAL")

score_models = models_ok / len(MODELS)
score_rg = rg_ok / len(RG)
score_tests = t_ok / len(TESTS)
score_urls = urls_ok / len(URLS)
score_tpl = tpl_ok / len(TEMPLATES)

global_score = (
    score_models * 0.20 +
    score_rg * 0.30 +
    score_urls * 0.15 +
    score_tpl * 0.15 +
    score_tests * 0.20
) * 100

print()
print("  Modeles   : " + str(models_ok) + "/" + str(len(MODELS)) + "  (" + f"{score_models*100:.1f}" + "%)")
print("  Regles    : " + str(rg_ok) + "/" + str(len(RG)) + "  (" + f"{score_rg*100:.1f}" + "%)")
print("  Tests     : " + str(t_ok) + "/" + str(len(TESTS)) + "  (" + f"{score_tests*100:.1f}" + "%)")
print("  URLs      : " + str(urls_ok) + "/" + str(len(URLS)) + "  (" + f"{score_urls*100:.1f}" + "%)")
print("  Templates : " + str(tpl_ok) + "/" + str(len(TEMPLATES)) + "  (" + f"{score_tpl*100:.1f}" + "%)")
print()
print("  " + "=" * 60)
print("  SCORE GLOBAL : " + f"{global_score:.1f}" + "%")
print("  " + "=" * 60)

h1("RESUME PAR PACK")
for pack in ["PACK_A", "PACK_B", "PACK_C"]:
    s = results["sections"].get(pack, {"p": 0, "f": 0, "w": 0})
    total = s["p"] + s["f"] + s["w"]
    pct = (s["p"] / total * 100) if total > 0 else 0
    status = "OK" if s["f"] == 0 else "INCOMPLET"
    print("  " + pack.ljust(10) + " : " + str(s["p"]) + "/" + str(total) + f" ({pct:.0f}%)" + " [" + status + "]")

h1("VERDICT FINAL")
if global_score >= 95:
    print("  PLATEFORME CONFORME AU PRD v2.0")
    print("  -> Pret pour deploiement")
elif global_score >= 85:
    print("  QUELQUES AMELIORATIONS POSSIBLES")
elif global_score >= 70:
    print("  PLUSIEURS MANQUES")
else:
    print("  CONFORMITE INSUFFISANTE")

if results["failed"] > 0:
    print()
    print("  ECHECS :")
    for s, m in results["details"]:
        if s == "FAIL":
            print("     XX " + m)

print()
print("=" * 72)
print("  Total : " + str(results["passed"]) + " passes / " + str(results["failed"]) + " echecs / " + str(results["warned"]) + " warnings")
print("=" * 72)
print()
