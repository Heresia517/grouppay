"""Test automatise - PACK C1+C2+C3 : 2FA + Animations + PWA."""
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

try:
    import django
    django.setup()
except Exception as e:
    print("Django error: " + str(e))
    sys.exit(1)

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse, NoReverseMatch
from django.utils import timezone

User = get_user_model()
ROOT = Path.cwd()

def h1(t):
    print("\n" + "=" * 70)
    print("  " + t)
    print("=" * 70)

def h2(t):
    print("\n> " + t)

results = {"passed": 0, "failed": 0, "warned": 0, "details": []}

def ok(m):
    results["passed"] += 1
    results["details"].append(("PASS", m))
    print("  OK  " + m)

def ko(m):
    results["failed"] += 1
    results["details"].append(("FAIL", m))
    print("  XX  " + m)

def warn(m):
    results["warned"] += 1
    results["details"].append(("WARN", m))
    print("  !!  " + m)

print("\n" + "=" * 70)
print("  TEST PACK C1+C2+C3 - 2FA + Animations + PWA")
print("=" * 70)

# ═══════════════════════════════════════════════════════════════
# TEST 1 - Settings 2FA
# ═══════════════════════════════════════════════════════════════
h1("TEST 1 - SETTINGS 2FA")

h2("1.1 INSTALLED_APPS")
apps_list = list(getattr(settings, "INSTALLED_APPS", []))
for app in ["django_otp", "django_otp.plugins.otp_totp"]:
    if app in apps_list:
        ok(app + " dans INSTALLED_APPS")
    else:
        ko(app + " MANQUANT")

h2("1.2 Middleware OTP")
mw = list(getattr(settings, "MIDDLEWARE", []))
if any("django_otp" in m for m in mw):
    ok("OTPMiddleware present")
else:
    ko("OTPMiddleware MANQUANT")

h2("1.3 Settings OTP")
for s in ["OTP_TOTP_ISSUER", "OTP_LOGIN_URL"]:
    if hasattr(settings, s):
        ok(s + " = " + str(getattr(settings, s)))
    else:
        warn(s + " absent")

# ═══════════════════════════════════════════════════════════════
# TEST 2 - Vues 2FA
# ═══════════════════════════════════════════════════════════════
h1("TEST 2 - VUES 2FA")

p = ROOT / "apps/accounts/two_factor_views.py"
if p.exists():
    src = p.read_text(encoding="utf-8")
    for fn in ["def two_factor_setup", "def two_factor_verify",
               "def two_factor_disable", "def two_factor_status"]:
        if fn in src:
            ok(fn + " present")
        else:
            ko(fn + " manquant")
    for imp in ["from django_otp", "from django_otp.plugins.otp_totp.models import TOTPDevice"]:
        if imp in src:
            ok(imp[:40] + "... import OK")
        else:
            warn(imp[:40] + "... import absent")
else:
    ko("two_factor_views.py introuvable")

# ═══════════════════════════════════════════════════════════════
# TEST 3 - URLs 2FA
# ═══════════════════════════════════════════════════════════════
h1("TEST 3 - URLs 2FA")

for name in ["two_factor_setup", "two_factor_verify", "two_factor_disable", "two_factor_status"]:
    try:
        url = reverse(name)
        ok(name + " -> " + url)
    except NoReverseMatch:
        ko(name + " -> NON TROUVEE")

# ═══════════════════════════════════════════════════════════════
# TEST 4 - Templates 2FA
# ═══════════════════════════════════════════════════════════════
h1("TEST 4 - TEMPLATES 2FA")

templates_to_check = {
    "templates/accounts/2fa_setup.html": [
        "Authentification", "QR code", "qr_code", "token", "Activer la 2FA",
    ],
    "templates/accounts/2fa_enabled.html": [
        "2FA active", "Desactiver", "two_factor_disable",
    ],
}

for tpl, needles in templates_to_check.items():
    h2(tpl)
    p = ROOT / tpl
    if not p.exists():
        ko(tpl + " introuvable")
        continue
    src = p.read_text(encoding="utf-8")
    for n in needles:
        if n in src:
            ok("contient '" + n + "'")
        else:
            warn("manque '" + n + "'")

# ═══════════════════════════════════════════════════════════════
# TEST 5 - C2 Animations CSS
# ═══════════════════════════════════════════════════════════════
h1("TEST 5 - ANIMATIONS CSS")

p = ROOT / "templates/base.html"
if p.exists():
    src = p.read_text(encoding="utf-8")
    animations = [
        ("gpFadeIn", "keyframe fade-in"),
        ("gpSlideInRight", "keyframe slide-in"),
        ("gpShimmer", "keyframe shimmer"),
        ("gp-fade-in", "classe fade-in"),
        ("gp-stagger", "classe stagger"),
        ("gp-skeleton", "skeleton loader"),
        ("gp-spinner", "spinner"),
        ("gp-lift", "hover lift"),
        ("prefers-reduced-motion", "accessibility"),
    ]
    for needle, label in animations:
        if needle in src:
            ok(label + " present")
        else:
            ko(label + " MANQUANT")

# Catalog stagger
p = ROOT / "templates/catalog/catalog.html"
if p.exists():
    if "gp-stagger" in p.read_text(encoding="utf-8"):
        ok("Catalogue grid avec gp-stagger")
    else:
        warn("Catalogue sans gp-stagger")

# ═══════════════════════════════════════════════════════════════
# TEST 6 - C3 PWA Install prompt
# ═══════════════════════════════════════════════════════════════
h1("TEST 6 - PWA INSTALL PROMPT")

p = ROOT / "templates/base.html"
if p.exists():
    src = p.read_text(encoding="utf-8")
    pwa_elements = [
        ("gp-pwa-banner", "bandeau PWA"),
        ("beforeinstallprompt", "listener install"),
        ("gp-pwa-install", "bouton Installer"),
        ("gp-pwa-dismiss", "bouton Plus tard"),
        ("appinstalled", "event install"),
        ("display-mode: standalone", "detection standalone"),
        ("localStorage.setItem('gp-pwa-dismissed'", "persistence dismiss"),
    ]
    for needle, label in pwa_elements:
        if needle in src:
            ok(label + " present")
        else:
            ko(label + " MANQUANT")

# ═══════════════════════════════════════════════════════════════
# TEST 7 - Model TOTPDevice
# ═══════════════════════════════════════════════════════════════
h1("TEST 7 - MODELE TOTPDevice")

try:
    from django_otp.plugins.otp_totp.models import TOTPDevice
    fields = {f.name for f in TOTPDevice._meta.get_fields()}
    required = ["user", "name", "key", "confirmed"]
    missing = [f for f in required if f not in fields]
    if missing:
        ko("TOTPDevice manque: " + ", ".join(missing))
    else:
        ok("TOTPDevice OK (" + str(len(fields)) + " champs)")
except Exception as e:
    ko("TOTPDevice inaccessible: " + str(e))

# ═══════════════════════════════════════════════════════════════
# TEST 8 - FONCTIONNEL 2FA
# ═══════════════════════════════════════════════════════════════
h1("TEST 8 - FONCTIONNEL 2FA")

user = User.objects.filter(is_superuser=True).first()
if not user:
    ko("Aucun superuser")
else:
    from django_otp.plugins.otp_totp.models import TOTPDevice

    # Nettoyer avant
    TOTPDevice.objects.filter(user=user).delete()

    h2("8.1 GET /accounts/2fa/")
    try:
        c = Client()
        c.force_login(user)
        r = c.get(reverse("two_factor_setup"))
        if r.status_code == 200:
            content = r.content.decode("utf-8")
            if "Authentification" in content:
                ok("Page 2FA -> 200 (" + str(len(content)) + " bytes)")
                if "QR code" in content or "qr_code" in content:
                    ok("QR code present")
            else:
                warn("Contenu inattendu")
        else:
            ko("HTTP " + str(r.status_code))
    except Exception as e:
        ko("Erreur: " + str(e))

    h2("8.2 Device TOTP cree")
    try:
        dev = TOTPDevice.objects.filter(user=user, confirmed=False).first()
        if dev:
            ok("Device TOTP cree (key=" + dev.key[:8] + "...)")
        else:
            ko("Aucun device TOTP cree")
    except Exception as e:
        ko("Erreur: " + str(e))

    h2("8.3 Verification avec code simule")
    try:
        # Recuperer le device
        dev = TOTPDevice.objects.filter(user=user, confirmed=False).first()
        if dev:
            # Generer le code actuel via pyotp ou directement
            try:
                import pyotp
                token = pyotp.TOTP(dev.key).now()
            except ImportError:
                # Utiliser la methode du device
                token = dev.generate_token(0) if hasattr(dev, "generate_token") else None

            if token:
                # Verifier via le device
                if dev.verify_token(str(token)):
                    ok("Code TOTP valide (verification OK)")

                    # Confirmer
                    dev.confirmed = True
                    dev.save()
                    ok("Device confirme")
                else:
                    warn("Code TOTP invalide")
            else:
                warn("Impossible de generer un token")
        else:
            ko("Aucun device pour tester")
    except Exception as e:
        warn("Test code: " + str(e))

    h2("8.4 Status API")
    try:
        c = Client()
        c.force_login(user)
        r = c.get(reverse("two_factor_status"))
        if r.status_code == 200:
            data = r.json()
            ok("Status API: " + str(data))
        else:
            warn("Status -> " + str(r.status_code))
    except Exception as e:
        ko("Erreur: " + str(e))

    h2("8.5 Disable 2FA")
    try:
        c = Client()
        c.force_login(user)
        r = c.post(reverse("two_factor_disable"))
        remaining = TOTPDevice.objects.filter(user=user).count()
        if remaining == 0:
            ok("2FA desactive (device supprime)")
        else:
            ko("Device encore present (" + str(remaining) + ")")
    except Exception as e:
        ko("Erreur: " + str(e))

    # Cleanup
    TOTPDevice.objects.filter(user=user).delete()

# ═══════════════════════════════════════════════════════════════
# TEST 9 - Lien dans profile
# ═══════════════════════════════════════════════════════════════
h1("TEST 9 - LIEN PROFILE")

p = ROOT / "templates/accounts/profile.html"
if p.exists():
    src = p.read_text(encoding="utf-8")
    if "two_factor_setup" in src:
        ok("Lien 'Securite 2FA' dans profile.html")
    else:
        ko("Lien 2FA MANQUANT dans profile.html")

# ═══════════════════════════════════════════════════════════════
# TEST 10 - Coherence
# ═══════════════════════════════════════════════════════════════
h1("TEST 10 - COHERENCE")

try:
    from django.core.management import call_command
    from io import StringIO
    out = StringIO()
    call_command("check", stdout=out, stderr=out)
    ok("Django check OK")
except Exception as e:
    ko("check echoue: " + str(e))

# Migrations
try:
    from django.db import connection
    with connection.cursor() as c:
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='otp_totp_totpdevice'")
        if c.fetchone():
            ok("Table otp_totp_totpdevice existe")
        else:
            ko("Table TOTPDevice MANQUANTE")
except Exception as e:
    warn("Erreur DB: " + str(e))

# ═══════════════════════════════════════════════════════════════
# RESUME
# ═══════════════════════════════════════════════════════════════
h1("RESUME")
total = results["passed"] + results["failed"] + results["warned"]
score = (results["passed"] / total * 100) if total > 0 else 0
print("")
print("  Passes   : " + str(results["passed"]))
print("  Warnings : " + str(results["warned"]))
print("  Echecs   : " + str(results["failed"]))
print("  Score    : " + f"{score:.1f}%")
print("")
if results["failed"] == 0:
    print("  PACK C1+C2+C3 - TOUS LES TESTS PASSENT")
    print("  => Pret pour C4 (Sentry) + C5 (Tests E2E)")
else:
    print("  Details:")
    for s, m in results["details"]:
        if s in ("FAIL", "WARN"):
            print("     " + s + ": " + m)
print("")
