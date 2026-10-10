"""Audit GroupPay v2.0 — Vérification PRD v2.0 + Inventaire exhaustif du projet."""
import os, sys, ast, json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

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
# CONSTANTES
# ═══════════════════════════════════════════════════════════════
EXCLUDE = {"venv", ".venv", "__pycache__", "migrations", ".git", ".kilo",
           "node_modules", "staticfiles", ".pytest_cache", "htmlcov", ".mypy_cache"}

# ═══════════════════════════════════════════════════════════════
# SCAN AST EXHAUSTIF (base de l'inventaire)
# ═══════════════════════════════════════════════════════════════
FILES = set()
FUNCS = set()
CLASSES = set()
files_index = {}                       # path -> {functions, classes, imports, lines}
all_functions = defaultdict(list)      # func_name -> [paths]
all_classes = defaultdict(list)        # class_name -> [paths]
total_lines = 0

for p in Path(".").rglob("*.py"):
    if set(p.parts) & EXCLUDE: continue
    if "audit_grouppay" in str(p): continue
    FILES.add(str(p))
    try:
        src = p.read_text(encoding="utf-8")
        lines = src.count("\n") + 1
        total_lines += lines
        tree = ast.parse(src)
        funcs, classes, imports = [], [], []
        for n in ast.walk(tree):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                funcs.append(n.name)
                all_functions[n.name].append(str(p))
            elif isinstance(n, ast.ClassDef):
                classes.append(n.name)
                all_classes[n.name].append(str(p))
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                for a in n.names: imports.append(a.name)
            elif isinstance(n, ast.ImportFrom):
                if n.module: imports.append(n.module)
        files_index[str(p)] = {"functions": funcs, "classes": classes,
                               "imports": imports, "lines": lines}
        FUNCS.update(funcs); CLASSES.update(classes)
    except Exception as e:
        files_index[str(p)] = {"error": str(e)}

has = lambda n: n in FUNCS or n in CLASSES
# ─── Détection par introspection des champs de modèles ───
FIELD_NAMES = set()
try:
    for _cfg in apps.get_app_configs():
        for _m in _cfg.get_models():
            for _f in _m._meta.get_fields():
                try:
                    FIELD_NAMES.add(_f.name)
                    if hasattr(_f, "attname"): FIELD_NAMES.add(_f.attname)
                except Exception: pass
except Exception: pass
has_any = lambda *names: any(n in FUNCS or n in CLASSES or n in FIELD_NAMES for n in names)

# ─── Détection textuelle des contraintes ───
CONSTRAINT_TEXT = ""
for _f in FILES:
    if _f.endswith("models.py"):
        try:
            CONSTRAINT_TEXT += Path(_f).read_text(errors="ignore")
        except Exception:
            pass




def h1(t):
    print("\n" + "=" * 72)
    print("  " + t)
    print("=" * 72)


def h2(t):
    print("\n> " + t)


results = {"passed": 0, "failed": 0, "warned": 0, "details": [], "sections": {}}
inventory = {}


def ok(m, section=None):
    results["passed"] += 1
    results["details"].append(("PASS", m))
    if section: results["sections"].setdefault(section, {"p": 0, "f": 0, "w": 0})["p"] += 1
    print("  OK  " + m)


def ko(m, section=None):
    results["failed"] += 1
    results["details"].append(("FAIL", m))
    if section: results["sections"].setdefault(section, {"p": 0, "f": 0, "w": 0})["f"] += 1
    print("  XX  " + m)


def warn(m, section=None):
    results["warned"] += 1
    results["details"].append(("WARN", m))
    if section: results["sections"].setdefault(section, {"p": 0, "f": 0, "w": 0})["w"] += 1
    print("  !!  " + m)


print("\n" + "╔" + "═" * 70 + "╗")
print("║" + " AUDIT GROUPPAY v2.0 — VERIFICATION + INVENTAIRE ".center(70) + "║")
print("╚" + "═" * 70 + "╝")

# ═══════════════════════════════════════════════════════════════
# SECTION 0 — INVENTAIRE COMPLET DE L'EXISTANT
# ═══════════════════════════════════════════════════════════════
h1("SECTION 0 — INVENTAIRE COMPLET (tout ce qui a été fait)")

h2("0.1 Statistiques globales")
print(f"  Fichiers Python       : {len(FILES)}")
print(f"  Lignes de code        : {total_lines}")
print(f"  Fonctions distinctes  : {len(FUNCS)}")
print(f"  Classes distinctes    : {len(CLASSES)}")
print(f"  Champs de modèles     : {len(FIELD_NAMES)}")

inventory["totals"] = {
    "py_files": len(FILES),
    "lines": total_lines,
    "functions": len(FUNCS),
    "classes": len(CLASSES),
}

h2("0.2 Applications Django installées")
apps_list = []
for cfg in apps.get_app_configs():
    n_models = len(list(cfg.get_models()))
    apps_list.append({"label": cfg.label, "name": cfg.name, "models": n_models})
    print(f"  - {cfg.label:<22} ({n_models} modèles)")
inventory["apps"] = apps_list

h2("0.3 Modèles enregistrés (introspection complète)")
models_inv = {}
for cfg in apps.get_app_configs():
    for m in cfg.get_models():
        key = f"{cfg.label}.{m.__name__}"
        fields = []
        for f in m._meta.get_fields():
            try:
                fields.append({
                    "name": f.name,
                    "type": f.get_internal_type() if hasattr(f, "get_internal_type") else type(f).__name__,
                })
            except Exception:
                pass
        models_inv[key] = {
            "verbose_name": str(m._meta.verbose_name),
            "db_table": m._meta.db_table,
            "n_fields": len(fields),
            "fields": fields,
        }
        print(f"  - {key:<42} {len(fields)} champs")
inventory["models"] = models_inv

h2("0.4 Fichiers Python par application")
by_app = defaultdict(list)
for f in sorted(FILES):
    parts = Path(f).parts
    if parts and parts[0] == "apps" and len(parts) > 1:
        by_app[parts[1]].append(f)
    elif parts and parts[0] in ("config", "tests"):
        by_app[parts[0]].append(f)
    else:
        by_app["_root"].append(f)
for app, flist in sorted(by_app.items()):
    print(f"\n  [{app}] — {len(flist)} fichiers")
    for f in sorted(flist)[:30]:
        info = files_index.get(f, {})
        nf = len(info.get("functions", []))
        nc = len(info.get("classes", []))
        nl = info.get("lines", 0)
        print(f"     {f:<62} ({nl:>5} L, {nf} fns, {nc} cls)")
    if len(flist) > 30:
        print(f"     ... +{len(flist)-30} autres fichiers")
inventory["files_by_app"] = {k: v for k, v in by_app.items()}

h2("0.5 Fonctions/classes clés détectées par domaine")
domains = {
    "Auth & Permissions":   ["IsRH", "IsAdmin", "IsRHOrAdmin", "IsSupplier", "IsOwner", "TenantModel"],
    "Panier & Commandes":   ["create_order_from_cart", "validate_order", "reject_order",
                             "add_to_cart", "remove_from_cart", "update_cart_item_qty",
                             "apply_coupon", "cleanup_expired_carts"],
    "Stock":                ["decrement_stock", "increment_stock", "adjust_stock",
                             "check_low_stock", "restore_stock", "resolve_alert"],
    "Retenue":              ["generate_export_batch", "confirm_deduction", "create_deduction",
                             "deduction_webhook"],
    "Livraisons":           ["create_delivery_for_order", "assign_courier", "mark_delivered",
                             "attempt_delivery"],
    "Documents PDF":        ["generate_purchase_order_pdf", "generate_invoice_pdf",
                             "generate_invoice_number", "get_or_create_invoice"],
    "Notifications":        ["send_email", "send_sms", "send_order_validated_email",
                             "send_order_delivered_email", "send_order_rejected_email",
                             "send_order_validated_sms", "send_order_delivered_sms"],
    "Avis produits":        ["submit_review", "delete_review", "average_rating",
                             "is_verified_purchase", "is_published"],
    "Wishlist collab":      ["toggle_wishlist", "vote_request", "request_create",
                             "update_request_status", "delete_request"],
    "2FA TOTP":             ["two_factor_setup", "two_factor_verify",
                             "two_factor_disable", "two_factor_status"],
    "Import CSV":           ["import_members_page", "import_members_csv", "import_members_template"],
    "Fournisseurs":         ["supplier_dashboard", "my_products", "product_form",
                             "toggle_product_active", "suppliers_overview"],
}
domain_summary = {}
for dom, names in domains.items():
    found = [n for n in names if has(n)]
    missing = [n for n in names if not has(n)]
    domain_summary[dom] = {"found": found, "missing": missing}
    status = "OK" if not missing else ("~" if found else "XX")
    print(f"  [{status:>2}] {dom:<22} : {len(found)}/{len(names)}")
    if found:
        print(f"        ✓ {', '.join(found)}")
    if missing:
        print(f"        ✗ {', '.join(missing)}")
inventory["domains"] = domain_summary

inventory["all_functions"] = sorted(FUNCS)
inventory["all_classes"] = sorted(CLASSES)

# ═══════════════════════════════════════════════════════════════
# SECTION 1 — MODELES (24 attendus)
# ═══════════════════════════════════════════════════════════════
h1("SECTION 1 — MODELES (24 attendus)")

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
        ok(f"{app_label}.{name} ({version})", "MODELES")
        models_ok += 1
    except LookupError:
        if version == "v2":
            ko(f"{app_label}.{name} MANQUANT (v2.0)", "MODELES")
        else:
            warn(f"{app_label}.{name} MANQUANT ({version})", "MODELES")

print(f"\n  → {models_ok}/{len(MODELS)} modèles présents")

# ═══════════════════════════════════════════════════════════════
# SECTION 2 — REGLES METIER (RG-01 → RG-45)
# ═══════════════════════════════════════════════════════════════
h1("SECTION 2 — REGLES METIER (RG-01 → RG-45)")

RG = {
    "RG-01": (["create_order_from_cart"], "Verrou stock anti-survente"),
    "RG-02": (["create_order_from_cart"], "Prix figé"),
    "RG-03": (["validate_order"], "Validation + Deduction"),
    "RG-04": (["reject_order"], "Refus restaure stock"),
    "RG-05": (["TenantModel"], "Isolation multi-tenant"),
    "RG-06": (["IsRH", "IsAdmin", "IsRHOrAdmin"], "Permissions RH/Admin"),
    "RG-07": (["reject_order"], "Refus avant livraison"),
    "RG-08": (["check_max_per_member"], "Max par membre"),
    "RG-09": (["cleanup_expired_carts"], "Panier expiré 30j"),
    "RG-10": (["validate_order"], "Non modifiable après validation"),
    "RG-11": (["expires_at", "expires_on", "expiration_date", "expires"], "Deduction expire 30j"),
    "RG-12": (["generate_export_batch"], "Export CSV EN_ATTENTE -> ENVOYEE"),
    "RG-13": (["generate_purchase_order_pdf"], "PDF bon de commande"),
    "RG-14": (["generate_export_batch"], "CSV format fixe"),
    "RG-15": (["confirm_deduction", "deduction_webhook"], "Double confirmation webhook"),
    "RG-16": (["create_delivery_for_order"], "Livraison auto"),
    "RG-17": (["assign_courier"], "Assignation livreur"),
    "RG-18": (["mark_delivered"], "Preuve livraison"),
    "RG-19": (["mark_delivered"], "LIVREE clôture order"),
    "RG-20": (["attempt_delivery"], "Retry livraison max 3"),
    "RG-21": (["check_low_stock"], "Alerte stock critique"),
    "RG-22": (["CheckConstraint"], "Stock négatif interdit"),
    "RG-23": (["decrement_stock", "ProductVariant"], "Variant stock"),
    "RG-24": (["submit_review"], "Avis acheteurs vérifiés"),
    "RG-25": (["unique_review_per_member_product", "UniqueConstraint", "unique_review"], "1 avis par membre/produit"),
    "RG-26": (["submit_review"], "Rating 1-5"),
    "RG-27": (["is_published", "is_visible", "moderated", "status"], "Avis modérables"),
    "RG-28": (["average_rating"], "Moyenne sur avis publiés"),
    "RG-29": (["delete_review"], "Suppression propre avis"),
    "RG-30": (["is_verified_purchase", "verified_purchase", "has_purchased", "is_verified"], "Badge achat vérifié"),
    "RG-31": (["StockMovement"], "Mouvement OUT"),
    "RG-32": (["StockMovement"], "Mouvement RESTORE"),
    "RG-33": (["adjust_stock"], "Mouvement ADJUST"),
    "RG-34": (["StockAlert"], "Création alerte seuil"),
    "RG-35": (["StockAlert"], "Résolution alerte"),
    "RG-36": (["supplier"], "Rattachement fournisseur"),
    "RG-37": (["my_products"], "Isolation produits fournisseur"),
    "RG-38": (["_is_owner"], "Modification propres produits"),
    "RG-39": (["suppliers_overview"], "Vue RH globale"),
    "RG-40": (["is_supplier_private", "is_private", "is_draft", "DRAFT"], "Produit privé brouillon"),
    "RG-41": (["request_create"], "Proposition produit"),
    "RG-42": (["request_create"], "Auto-vote auteur"),
    "RG-43": (["unique_vote_per_member_request", "UniqueConstraint", "unique_vote"], "1 vote par membre"),
    "RG-44": (["vote_request"], "Vote toggle"),
    "RG-45": (["update_request_status"], "RH change statut"),
}

rg_ok = 0
for rg, (proofs, desc) in RG.items():
    found = [p for p in proofs if has_any(p)]
    # RG-25 / RG-43 : UniqueConstraint dans Meta.constraints
    if rg == "RG-25" and not found and "unique_review_per_member_product" in CONSTRAINT_TEXT:
        found = ["unique_review_per_member_product"]
    if rg == "RG-43" and not found and "unique_vote_per_member_request" in CONSTRAINT_TEXT:
        found = ["unique_vote_per_member_request"]
    if rg == "RG-22" and not found:
        for f in FILES:
            if f.endswith("models.py"):
                try:
                    if "CheckConstraint" in Path(f).read_text(errors="ignore"):
                        found = ["CheckConstraint"]
                        break
                except Exception:
                    pass
    if found:
        ok(f"{rg} : {desc}", "RG")
        rg_ok += 1
    else:
        ko(f"{rg} : {desc} — MANQUANT", "RG")

print(f"\n  → {rg_ok}/{len(RG)} règles métier")

# ═══════════════════════════════════════════════════════════════
# SECTION 3 — PACK A (RH Essentials)
# ═══════════════════════════════════════════════════════════════
h1("SECTION 3 — PACK A : RH ESSENTIALS")

h2("A1. Import CSV membres")
for fn, desc in [("def import_members_page", "Vue page import"),
                 ("def import_members_csv", "Vue traitement CSV"),
                 ("def import_members_template", "Template CSV download"),
                 ("import_members", "URL import")]:
    _found = has_any(fn) or any(
        ("import_members" in Path(f).read_text(errors="ignore"))
        for f in FILES if f.endswith("urls.py"))
    (ok if _found else ko)(desc, "PACK_A")

h2("A2. Emails HTML")
for fn, desc in [("send_email", "Service envoi"),
                 ("send_order_validated_email", "Email validée"),
                 ("send_order_delivered_email", "Email livrée"),
                 ("send_order_rejected_email", "Email refusée"),
                 ("send_order_shipping_email", "Email en livraison")]:
    (ok if has(fn) else ko)(desc, "PACK_A")

for tpl in ["order_validated", "order_delivered", "order_rejected", "order_shipping"]:
    p = Path(f"templates/emails/{tpl}.html")
    (ok if p.exists() else ko)(f"Template email/{tpl}.html", "PACK_A")

h2("A3. SMS")
for fn, desc in [("send_sms", "Service SMS"),
                 ("send_order_validated_sms", "SMS validée"),
                 ("send_order_delivered_sms", "SMS livrée"),
                 ("send_order_rejected_sms", "SMS refusée")]:
    (ok if has(fn) else ko)(desc, "PACK_A")

h2("A4. Factures PDF")
for fn, desc in [("generate_invoice_number", "Numérotation factures"),
                 ("generate_invoice_pdf", "Génération PDF"),
                 ("get_or_create_invoice", "Helper facture"),
                 ("preview_invoice_html", "Preview HTML"),
                 ("download_invoice_pdf", "Download PDF")]:
    (ok if has(fn) else ko)(desc, "PACK_A")

h2("A5. Dashboard retenue")
for fn, desc in [("deductions_dashboard", "Dashboard retenue"),
                 ("preview_export", "Aperçu CSV"),
                 ("generate_export", "Génération CSV"),
                 ("download_batch", "Download batch")]:
    (ok if has(fn) else ko)(desc, "PACK_A")

h2("A6. Espace fournisseur")
(ok if has("supplier_dashboard") else ko)("Dashboard fournisseur", "PACK_A")

# ═══════════════════════════════════════════════════════════════
# SECTION 4 — PACK B (Marketplace)
# ═══════════════════════════════════════════════════════════════
h1("SECTION 4 — PACK B : MARKETPLACE")

h2("B1. Avis produits")
for fn in ["product_reviews", "submit_review", "delete_review"]:
    (ok if has(fn) else ko)(fn + " présent", "PACK_B")

h2("B2. Stock avancé")
for fn in ["stock_dashboard", "product_stock_history", "adjust_stock", "resolve_alert",
           "decrement_stock", "increment_stock", "check_low_stock"]:
    (ok if has(fn) else ko)(fn + " présent", "PACK_B")

h2("B3. Multi-fournisseurs")
for fn in ["my_products", "product_form", "toggle_product_active",
           "delete_product", "suppliers_overview"]:
    (ok if has(fn) else ko)(fn + " présent", "PACK_B")

h2("B4. Wishlist collaborative")
for fn in ["requests_list", "request_create", "vote_request",
           "delete_request", "update_request_status"]:
    (ok if has(fn) else ko)(fn + " présent", "PACK_B")

# ═══════════════════════════════════════════════════════════════
# SECTION 5 — PACK C (Professional)
# ═══════════════════════════════════════════════════════════════
h1("SECTION 5 — PACK C : PROFESSIONAL")

h2("C1. 2FA TOTP")
(ok if "django_otp" in settings.INSTALLED_APPS else ko)("django_otp dans INSTALLED_APPS", "PACK_C")
(ok if "django_otp.plugins.otp_totp" in settings.INSTALLED_APPS else ko)("otp_totp dans INSTALLED_APPS", "PACK_C")
(ok if any("django_otp" in m for m in settings.MIDDLEWARE) else ko)("OTPMiddleware", "PACK_C")
for fn in ["two_factor_setup", "two_factor_verify", "two_factor_disable", "two_factor_status"]:
    (ok if has(fn) else ko)(fn + " présent", "PACK_C")

h2("C2. Animations")
p = Path("templates/base.html")
if p.exists():
    src = p.read_text(encoding="utf-8")
    for needle, desc in [("gpFadeIn", "Fade-in keyframe"),
                         ("gp-stagger", "Stagger class"),
                         ("gp-skeleton", "Skeleton loader"),
                         ("gp-spinner", "Spinner"),
                         ("prefers-reduced-motion", "Accessibility")]:
        (ok if needle in src else ko)(desc, "PACK_C")

h2("C3. PWA Install prompt")
if p.exists():
    for needle, desc in [("gp-pwa-banner", "Bandeau install"),
                         ("beforeinstallprompt", "Listener install"),
                         ("gp-pwa-install", "Bouton installer"),
                         ("appinstalled", "Event install")]:
        (ok if needle in src else ko)(desc, "PACK_C")

h2("C4. Sentry")
for var in ["SENTRY_DSN", "SENTRY_ENVIRONMENT"]:
    if hasattr(settings, var):
        ok(f"{var} configuré", "PACK_C")
    else:
        warn(f"{var} absent (opt-in)", "PACK_C")
(ok if has("health") else ko)("Endpoint /health/", "PACK_C")

h2("C5. Tests E2E")
e2e_files = list(Path("tests/e2e").rglob("*.py")) if Path("tests/e2e").exists() else []
(ok if e2e_files else ko)(f"{len(e2e_files)} fichiers E2E", "PACK_C")

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
        ok(t, "TESTS"); t_ok += 1
    else:
        warn(t + " manquant", "TESTS")
print(f"\n  → {t_ok}/{len(TESTS)} tests")

# ═══════════════════════════════════════════════════════════════
# SECTION 7 — URLs
# ═══════════════════════════════════════════════════════════════
h1("SECTION 7 — URLs / ROUTES")

fake_id = uuid.uuid4()
URLS = [
    ("catalog", None), ("product_detail", "product_id"), ("view_cart", None),
    ("add_to_cart", "product_id"), ("remove_from_cart", "item_id"),
    ("update_cart_item_qty", "item_id"), ("apply_coupon", None), ("remove_coupon", None),
    ("create_order", None), ("my_orders", None), ("order_detail", "order_id"),
    ("download_pdf", "order_id"), ("preview_pdf", "order_id"),
    ("preview_order_html", "order_id"), ("preview_invoice_html", "order_id"),
    ("download_invoice_pdf", "order_id"), ("profile", None), ("save_theme", None),
    ("wishlist", None), ("toggle_wishlist", "product_id"), ("requests_list", None),
    ("request_create", None), ("vote_request", "request_id"),
    ("rh_dashboard", None), ("bulk_validate", None), ("bulk_reject", None),
    ("export_dashboard_excel", None), ("export_dashboard_pdf", None),
    ("deductions_dashboard", None), ("preview_export", None),
    ("generate_export", None), ("stock_dashboard", None),
    ("stock_history", "product_id"), ("adjust_stock", "product_id"),
    ("resolve_alert", "alert_id"), ("supplier_dashboard", None),
    ("supplier_my_products", None), ("supplier_product_new", None),
    ("suppliers_overview", None), ("import_members", None),
    ("import_members_upload", None), ("import_members_template", None),
    ("product_reviews", "product_id"), ("submit_review", "product_id"),
    ("two_factor_setup", None), ("two_factor_verify", None),
    ("two_factor_disable", None), ("two_factor_status", None),
    ("notif_unread_count", None), ("notif_list", None), ("health_check", None),
]

urls_ok = 0
for name, arg in URLS:
    try:
        if arg: reverse(name, kwargs={arg: fake_id})
        else: reverse(name)
        urls_ok += 1
    except NoReverseMatch:
        ko(f"URL '{name}' NON TROUVÉE", "URLS")
    except Exception as e:
        warn(f"URL '{name}' : {e}", "URLS")
print(f"\n  → {urls_ok}/{len(URLS)} URLs résolues")

# ═══════════════════════════════════════════════════════════════
# SECTION 8 — TEMPLATES
# ═══════════════════════════════════════════════════════════════
h1("SECTION 8 — TEMPLATES")

TEMPLATES = [
    "templates/base.html", "templates/components/navbar.html",
    "templates/components/footer.html", "templates/components/product_card.html",
    "templates/catalog/catalog.html", "templates/catalog/reviews.html",
    "templates/catalog/_stars.html", "templates/catalog/stock_dashboard.html",
    "templates/catalog/stock_history.html", "templates/catalog/supplier_products.html",
    "templates/catalog/supplier_product_form.html", "templates/catalog/suppliers_overview.html",
    "templates/catalog/supplier_dashboard.html", "templates/catalog/requests_list.html",
    "templates/catalog/request_form.html", "templates/orders/cart.html",
    "templates/orders/cart_badge.html", "templates/orders/my_orders.html",
    "templates/orders/order_detail.html", "templates/accounts/profile.html",
    "templates/accounts/wishlist.html", "templates/accounts/2fa_setup.html",
    "templates/accounts/2fa_enabled.html", "templates/admin/dashboard.html",
    "templates/admin/dashboard_pdf.html", "templates/admin/import_members.html",
    "templates/documents/invoice.html", "templates/documents/invoice_pdf.html",
    "templates/documents/preview.html", "templates/deductions/dashboard.html",
    "templates/deductions/_preview.html", "templates/emails/order_validated.html",
    "templates/emails/order_delivered.html", "templates/emails/order_rejected.html",
    "templates/emails/order_shipping.html",
]
tpl_ok = 0
for t in TEMPLATES:
    if Path(t).exists(): tpl_ok += 1
    else: ko(f"{t} MANQUANT", "TEMPLATES")
print(f"\n  → {tpl_ok}/{len(TEMPLATES)} templates")

# ═══════════════════════════════════════════════════════════════
# SECTION 9 — SETTINGS & INFRA
# ═══════════════════════════════════════════════════════════════
h1("SECTION 9 — SETTINGS & INFRA")

for desc, val in [
    ("SESSION_ENGINE cached_db", hasattr(settings, "SESSION_ENGINE") and "cached_db" in settings.SESSION_ENGINE),
    ("CACHES configuré", hasattr(settings, "CACHES")),
    ("REST_FRAMEWORK", hasattr(settings, "REST_FRAMEWORK")),
    ("OTP_TOTP_ISSUER", hasattr(settings, "OTP_TOTP_ISSUER")),
    ("SITE_URL", hasattr(settings, "SITE_URL")),
    ("AFRICASTALKING_USERNAME", hasattr(settings, "AFRICASTALKING_USERNAME")),
]:
    (ok if val else ko)(desc, "INFRA")

for f in ["Dockerfile", "docker-compose.yml", ".github/workflows/ci.yml",
          "pytest.ini", "requirements.txt", "config/celery.py", "config/asgi.py"]:
    (ok if Path(f).exists() else ko)(f, "INFRA")

for f in ["static/manifest.webmanifest", "static/sw.js",
          "static/img/icon-192.svg", "static/img/icon-512.svg"]:
    (ok if Path(f).exists() else ko)(f, "INFRA")

# ═══════════════════════════════════════════════════════════════
# SECTION 10 — SERVICES MÉTIER
# ═══════════════════════════════════════════════════════════════
h1("SECTION 10 — SERVICES MÉTIER")

SERVICES = [
    "apps/orders/services.py", "apps/catalog/services.py",
    "apps/catalog/review_views.py", "apps/catalog/stock_views.py",
    "apps/catalog/supplier_views.py", "apps/catalog/supplier_product_views.py",
    "apps/catalog/request_views.py", "apps/deductions/services.py",
    "apps/deductions/views.py", "apps/deductions/webhooks.py",
    "apps/deductions/tasks.py", "apps/deliveries/services.py",
    "apps/documents/services.py", "apps/documents/views.py",
    "apps/documents/invoice_service.py", "apps/notifications/email_service.py",
    "apps/notifications/sms_service.py", "apps/notifications/signals.py",
    "apps/notifications/consumers.py", "apps/notifications/routing.py",
    "apps/audit/models.py", "apps/audit/middleware.py",
    "apps/accounts/permissions.py", "apps/accounts/two_factor_views.py",
    "apps/accounts/views.py", "apps/orders/dashboard_views.py",
    "apps/orders/export_views.py", "apps/orders/tasks.py",
    "apps/orders/context_processors.py",
]
svc_ok = 0
for s in SERVICES:
    if Path(s).exists(): svc_ok += 1
    else: ko(f"{s} MANQUANT", "SERVICES")
print(f"\n  → {svc_ok}/{len(SERVICES)} services")

# ═══════════════════════════════════════════════════════════════
# SCORE FINAL
# ═══════════════════════════════════════════════════════════════
h1("SCORE FINAL — CONFORMITE PRD v2.0")

score_models = models_ok / len(MODELS)
score_rg = rg_ok / len(RG)
score_tests = t_ok / len(TESTS)
score_urls = urls_ok / len(URLS)
score_tpl = tpl_ok / len(TEMPLATES)
score_svc = svc_ok / len(SERVICES)

global_score = (
    score_models * 0.20 + score_rg * 0.30 + score_urls * 0.15 +
    score_tpl * 0.15 + score_svc * 0.10 + score_tests * 0.10
) * 100

print()
print(f"  Modèles      : {models_ok}/{len(MODELS)}  ({score_models*100:.1f}%)")
print(f"  Règles       : {rg_ok}/{len(RG)}  ({score_rg*100:.1f}%)")
print(f"  Tests        : {t_ok}/{len(TESTS)}  ({score_tests*100:.1f}%)")
print(f"  URLs         : {urls_ok}/{len(URLS)}  ({score_urls*100:.1f}%)")
print(f"  Templates    : {tpl_ok}/{len(TEMPLATES)}  ({score_tpl*100:.1f}%)")
print(f"  Services     : {svc_ok}/{len(SERVICES)}  ({score_svc*100:.1f}%)")
print()
print("  " + "=" * 60)
print(f"  SCORE GLOBAL : {global_score:.1f}%")
print("  " + "=" * 60)

h1("RESUME PAR PACK")
for pack in ["PACK_A", "PACK_B", "PACK_C"]:
    s = results["sections"].get(pack, {"p": 0, "f": 0, "w": 0})
    total = s["p"] + s["f"] + s["w"]
    pct = (s["p"] / total * 100) if total > 0 else 0
    status = "OK" if s["f"] == 0 else "INCOMPLET"
    print(f"  {pack:<10} : {s['p']}/{total} ({pct:.0f}%) [{status}]")

h1("VERDICT FINAL")
if global_score >= 95:
    print("  ✓ PLATEFORME CONFORME AU PRD v2.0")
    print("  → Prêt pour déploiement en production")
elif global_score >= 85:
    print("  ~ QUELQUES AMELIORATIONS POSSIBLES")
    print("  → Corriger les manques ci-dessus")
elif global_score >= 70:
    print("  ! PLUSIEURS MANQUES")
    print("  → Compléter les features manquantes")
else:
    print("  XX CONFORMITE INSUFFISANTE")
    print("  → Retravailler les fondations")

if results["failed"] > 0:
    print("\n  DETAIL DES ECHECS :")
    for s, m in results["details"]:
        if s == "FAIL":
            print("     XX " + m)

print()
print("=" * 72)
print(f"  Total : {results['passed']} passes / {results['failed']} échecs / {results['warned']} warnings")
print("=" * 72)

# ═══════════════════════════════════════════════════════════════
# EXPORT INVENTAIRE — JSON + MARKDOWN
# ═══════════════════════════════════════════════════════════════
h1("EXPORT DE L'INVENTAIRE")

inventory["timestamp"] = datetime.now().isoformat(timespec="seconds")
inventory["audit_summary"] = {
    "passed": results["passed"],
    "failed": results["failed"],
    "warned": results["warned"],
    "global_score": round(global_score, 2),
    "sections": results["sections"],
}
inventory["failures"] = [m for s, m in results["details"] if s == "FAIL"]
inventory["warnings"] = [m for s, m in results["details"] if s == "WARN"]

# JSON
json_path = Path("audit_inventaire.json")
json_path.write_text(json.dumps(inventory, ensure_ascii=False, indent=2, default=str),
                     encoding="utf-8")
print(f"  ✓ {json_path} écrit ({json_path.stat().st_size // 1024} Ko)")

# Markdown
md = []
md.append(f"# Inventaire GroupPay v2.0 — {inventory['timestamp']}\n")
md.append(f"**Score global PRD : {global_score:.1f}%**  ")
md.append(f"**{results['passed']} OK / {results['failed']} échecs / {results['warned']} warnings**\n")

md.append("## Statistiques\n")
t = inventory["totals"]
md.append(f"- Fichiers Python : **{t['py_files']}**")
md.append(f"- Lignes de code : **{t['lines']}**")
md.append(f"- Fonctions : **{t['functions']}**")
md.append(f"- Classes : **{t['classes']}**\n")

md.append("## Applications Django\n")
md.append("| App | Modèles |")
md.append("|-----|---------|")
for a in inventory["apps"]:
    md.append(f"| {a['label']} | {a['models']} |")
md.append("")

md.append("## Modèles (introspection)\n")
md.append("| Modèle | Table | Champs |")
md.append("|--------|-------|--------|")
for k, v in sorted(inventory["models"].items()):
    md.append(f"| {k} | `{v['db_table']}` | {v['n_fields']} |")
md.append("")

md.append("## Domaines fonctionnels\n")
md.append("| Domaine | Présents | Manquants |")
md.append("|---------|----------|-----------|")
for dom, data in inventory["domains"].items():
    md.append(f"| {dom} | {len(data['found'])} | {len(data['missing'])} |")
md.append("")

if inventory["failures"]:
    md.append("## Échecs\n")
    for f in inventory["failures"]:
        md.append(f"- {f}")
    md.append("")

if inventory["warnings"]:
    md.append("## Warnings\n")
    for w in inventory["warnings"]:
        md.append(f"- {w}")
    md.append("")

md.append("## Fonctions détectées (extrait)\n")
md.append("```")
md.append(", ".join(inventory["all_functions"][:200]))
md.append("```\n")

md_path = Path("INVENTAIRE.md")
md_path.write_text("\n".join(md), encoding="utf-8")
print(f"  ✓ {md_path} écrit ({md_path.stat().st_size // 1024} Ko)")

print()
print("=" * 72)
print("  INVENTAIRE COMPLET — Consulter INVENTAIRE.md et audit_inventaire.json")
print("=" * 72)
print()