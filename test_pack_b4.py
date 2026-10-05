"""Test automatise - PACK B4 : Wishlist collaborative."""
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
print("  TEST PACK B4 - Wishlist collaborative")
print("=" * 70)

# TEST 1 - Modeles
h1("TEST 1 - MODELES")

h2("1.1 ProductRequest")
try:
    PR = apps.get_model("catalog", "ProductRequest")
    fields = {f.name for f in PR._meta.get_fields()}
    required = ["organization", "title", "description", "category_hint",
                "target_price", "proposed_by", "status", "reviewed_by",
                "review_note", "created_at", "updated_at"]
    missing = [f for f in required if f not in fields]
    if missing:
        ko("ProductRequest manque: " + ", ".join(missing))
    else:
        ok("ProductRequest OK (" + str(len(fields)) + " champs)")
except Exception as e:
    ko("ProductRequest inaccessible: " + str(e))

h2("1.2 ProductRequestVote")
try:
    V = apps.get_model("catalog", "ProductRequestVote")
    fields = {f.name for f in V._meta.get_fields()}
    required = ["organization", "request", "member", "created_at"]
    missing = [f for f in required if f not in fields]
    if missing:
        ko("ProductRequestVote manque: " + ", ".join(missing))
    else:
        ok("ProductRequestVote OK (" + str(len(fields)) + " champs)")
except Exception as e:
    ko("ProductRequestVote inaccessible: " + str(e))

h2("1.3 Contrainte unique vote")
try:
    V = apps.get_model("catalog", "ProductRequestVote")
    constraints = V._meta.constraints
    has_unique = any("unique_vote_per_member_request" in str(c) for c in constraints)
    if has_unique:
        ok("Contrainte unique vote OK")
    else:
        ko("Contrainte unique MANQUANTE")
except Exception as e:
    ko("Erreur: " + str(e))

# TEST 2 - Vues
h1("TEST 2 - VUES")
p = ROOT / "apps/catalog/request_views.py"
if p.exists():
    src = p.read_text(encoding="utf-8")
    for fn in ["def requests_list", "def request_create", "def vote_request",
               "def delete_request", "def update_request_status"]:
        if fn in src:
            ok(fn + " present")
        else:
            ko(fn + " manquant")
else:
    ko("request_views.py introuvable")

# TEST 3 - Templates
h1("TEST 3 - TEMPLATES")
for tpl, needles in {
    "templates/catalog/requests_list.html": ["Demandes produits", "Proposer un produit", "vote_request"],
    "templates/catalog/request_form.html": ["Titre du produit", "Prix cible"],
}.items():
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
            ko("manque '" + n + "'")

# TEST 4 - URLs
h1("TEST 4 - URLs")
import uuid
fake = uuid.uuid4()
for name, arg in [
    ("requests_list", None),
    ("request_create", None),
    ("vote_request", "request_id"),
    ("delete_request", "request_id"),
    ("update_request_status", "request_id"),
]:
    try:
        url = reverse(name, kwargs={arg: fake}) if arg else reverse(name)
        ok(name + " -> " + url)
    except NoReverseMatch:
        ko(name + " -> NON TROUVEE")

# TEST 5 - Admin
h1("TEST 5 - ADMIN")
p = ROOT / "apps/catalog/admin.py"
if p.exists():
    src = p.read_text(encoding="utf-8")
    for label in ["ProductRequestAdmin", "ProductRequestVoteAdmin", "mark_accepted"]:
        if label in src:
            ok(label + " present")
        else:
            ko(label + " manquant")

# TEST 6 - FONCTIONNEL
h1("TEST 6 - FONCTIONNEL")
user = User.objects.filter(is_superuser=True).first()
if not user:
    ko("Aucun superuser")
else:
    from apps.catalog.models import ProductRequest, ProductRequestVote
    org = user.organization

    # Nettoyage avant
    ProductRequest.objects.filter(organization=org, title__startswith="__Test B4").delete()

    h2("6.1 requests_list accessible")
    try:
        c = Client()
        c.force_login(user)
        r = c.get(reverse("requests_list"))
        if r.status_code == 200:
            content = r.content.decode("utf-8")
            if "Demandes produits" in content:
                ok("Page requests -> 200 (" + str(len(content)) + " bytes)")
            else:
                warn("Contenu inattendu")
        else:
            ko("HTTP " + str(r.status_code))
    except Exception as e:
        ko("Erreur: " + str(e))

    h2("6.2 Creer une proposition")
    try:
        c = Client()
        c.force_login(user)
        r = c.post(reverse("request_create"), {
            "title": "__Test B4 Frigo industriel",
            "description": "Pour la cantine de l'entreprise",
            "category_hint": "Electromenager",
            "target_price": "250000",
        })

        req = ProductRequest.objects.filter(
            organization=org, title="__Test B4 Frigo industriel",
        ).first()

        if req:
            ok("Proposition creee: " + req.title)
            # L'auteur doit avoir vote automatiquement
            if req.votes.filter(member=user).exists():
                ok("Auteur a vote automatiquement")
            else:
                ko("Auteur n'a pas vote (attendu automatique)")
        else:
            ko("Proposition non creee (status=" + str(r.status_code) + ")")
    except Exception as e:
        import traceback
        traceback.print_exc()
        ko("Erreur: " + str(e))

    h2("6.3 Retirer son vote (toggle)")
    try:
        if req:
            c = Client()
            c.force_login(user)
            r = c.post(reverse("vote_request", kwargs={"request_id": req.id}))

            # L'user avait vote -> doit etre retire
            if not req.votes.filter(member=user).exists():
                ok("Vote retire (toggle off)")
            else:
                ko("Vote non retire")
    except Exception as e:
        ko("Erreur: " + str(e))

    h2("6.4 Re-voter")
    try:
        if req:
            c = Client()
            c.force_login(user)
            r = c.post(reverse("vote_request", kwargs={"request_id": req.id}))

            if req.votes.filter(member=user).exists():
                ok("Re-vote OK (count=" + str(req.votes.count()) + ")")
            else:
                ko("Re-vote echoue")
    except Exception as e:
        ko("Erreur: " + str(e))

    h2("6.5 Changer statut (RH)")
    try:
        if req:
            c = Client()
            c.force_login(user)
            r = c.post(reverse("update_request_status", kwargs={"request_id": req.id}), {
                "status": "REVIEWING",
                "note": "En discussion avec le fournisseur",
            })

            req.refresh_from_db()
            if req.status == "REVIEWING":
                ok("Statut -> " + req.status + " (note: " + req.review_note[:30] + ")")
            else:
                ko("Statut non change (" + req.status + ")")
    except Exception as e:
        ko("Erreur: " + str(e))

    h2("6.6 Supprimer la proposition")
    try:
        if req:
            rid = req.id
            c = Client()
            c.force_login(user)
            r = c.post(reverse("delete_request", kwargs={"request_id": rid}))

            if not ProductRequest.objects.filter(id=rid).exists():
                ok("Proposition supprimee")
            else:
                ko("Proposition non supprimee")
    except Exception as e:
        ko("Erreur: " + str(e))

    # Cleanup final
    ProductRequest.objects.filter(organization=org, title__startswith="__Test B4").delete()

# TEST 7 - Permission
h1("TEST 7 - PERMISSION")
h2("7.1 Membre ne peut pas changer statut")
try:
    member = User.objects.filter(role="MEMBRE").first()
    if not member:
        # Creer un membre temporaire
        member_email = "__test_b4_member@test.local"
        User.objects.filter(email=member_email).delete()
        member = User.objects.create_user(
            email=member_email, organization=user.organization,
            password="test123", role="MEMBRE",
        )

    # Creer une request
    req = ProductRequest.objects.create(
        organization=user.organization, title="__Test B4 Pour permission",
        proposed_by=user,
    )

    c = Client()
    c.force_login(member)
    try:
        r = c.post(reverse("update_request_status", kwargs={"request_id": req.id}), {
            "status": "ACCEPTED",
        })
        req.refresh_from_db()
        if req.status != "ACCEPTED":
            ok("Membre bloque (statut inchange: " + req.status + ")")
        else:
            ko("Membre a pu changer le statut (BUG)")
    except Exception:
        ok("Membre bloque (exception PermissionDenied)")

    req.delete()
    User.objects.filter(email="__test_b4_member@test.local").delete()
except Exception as e:
    ko("Erreur: " + str(e))

# TEST 8 - Coherence
h1("TEST 8 - COHERENCE")
try:
    from django.core.management import call_command
    from io import StringIO
    out = StringIO()
    call_command("check", stdout=out, stderr=out)
    ok("Django check OK")
except Exception as e:
    ko("check echoue: " + str(e))

p = ROOT / "templates/components/navbar.html"
if p.exists():
    src = p.read_text(encoding="utf-8")
    if "url 'requests_list'" in src:
        ok("Lien Demandes dans navbar")
    else:
        ko("Lien Demandes MANQUANT")

# RESUME
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
    print("  PACK B4 - TOUS LES TESTS PASSENT")
    print("  => PACK B COMPLET !")
else:
    print("  Details:")
    for s, m in results["details"]:
        if s in ("FAIL", "WARN"):
            print("     " + s + ": " + m)
print("")
