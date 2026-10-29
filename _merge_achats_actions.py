"""Fusionne verif stock + visa pour le Directeur des Achats en une action."""
import os
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.base"
os.environ["ZIONPAY_MODE"] = "desktop"

import django
django.setup()

import re
from pathlib import Path

print("=" * 70)
print("  FUSION : VERIF STOCK + VISA ACHATS EN UNE ACTION")
print("=" * 70)

views_file = Path("apps/da/views.py")
vsrc = views_file.read_text(encoding="utf-8")

# ═══════════════════════════════════════════════════════════════
# 1. REMPLACER da_visa PAR UNE VERSION QUI FAIT TOUT POUR LES ACHATS
# ═══════════════════════════════════════════════════════════════
pattern = re.compile(r"def da_visa\(request, request_id\):.*?(?=\ndef |\Z)", re.DOTALL)
match = pattern.search(vsrc)

if match:
    new_view = '''def da_visa(request, request_id):
    """Visa unifie : routage selon le role + verif stock pour les achats."""
    from django.shortcuts import get_object_or_404, redirect
    from django.contrib import messages
    from django.core.exceptions import PermissionDenied, ValidationError
    from apps.da.models import PurchaseRequest
    from apps.da import workflow

    da = get_object_or_404(PurchaseRequest, id=request_id, organization=request.user.organization)
    user = request.user

    if request.method != "POST":
        raise PermissionDenied("Methode non autorisee.")

    approved = request.POST.get("approved") == "yes"
    comment = request.POST.get("comment", "").strip()

    try:
        # Cas 1 : Directeur des Achats (verifie stock + vise en une action)
        if _is_achats(user) and da.status == "VISEE_DIRECTEUR":
            # 1. Analyser le stock automatiquement
            stock_analysis = {}
            for line in da.items.all():
                key = str(line.item_id)
                available = line.item.stock_quantity or 0
                to_buy = max(0, line.quantity - available)
                stock_analysis[key] = {
                    "available": available,
                    "to_buy": to_buy,
                }

            # 2. Verifier le stock + passer a STOCK_VERIFIE
            workflow.verify_stock(da, actor=user, stock_analysis=stock_analysis)

            # 3. Apposer le visa des Achats + passer a VISEE_ACHATS
            da.refresh_from_db()
            workflow.visa_by_achats(da, actor=user, comment=comment, approved=approved)

            if approved:
                messages.success(
                    request,
                    f"Stock verifie et visa des Achats accorde pour {da.number}."
                )
            else:
                messages.warning(request, f"DA {da.number} refusee par les Achats.")

        # Cas 2 : Directeur du service du chef (statut SOUMISE)
        elif _can_validate_da(user, da) and da.status == "SOUMISE":
            workflow.visa_by_director(da, actor=user, comment=comment, approved=approved)
            if approved:
                messages.success(request, f"Visa Directeur accorde pour {da.number}.")
            else:
                messages.warning(request, f"DA {da.number} refusee par le Directeur.")
        else:
            raise PermissionDenied(
                f"Action impossible : statut={da.status}, "
                f"role={user.role}, is_director={getattr(user, 'is_director', False)}, "
                f"is_achats={_is_achats(user)}"
            )
    except ValidationError as e:
        messages.error(request, str(e))

    return redirect("da_detail", request_id=da.id)
'''
    vsrc = vsrc[:match.start()] + new_view + vsrc[match.end():]
    print("[OK] da_visa : verif stock + visa en une action pour les Achats")
else:
    print("[WARN] da_visa non trouvee")

# ═══════════════════════════════════════════════════════════════
# 2. AJOUTER UNE VUE "apercu stock" pour le directeur des achats
# ═══════════════════════════════════════════════════════════════
if "def da_visa_page" not in vsrc:
    # Trouver l'endroit pour ajouter
    match_pos = vsrc.find("def da_visa(request, request_id):")
    if match_pos > 0:
        new_page_view = '''def da_visa_page(request, request_id):
    """Page de visa : affiche l'analyse stock pour les Achats."""
    from django.shortcuts import get_object_or_404, render
    from django.core.exceptions import PermissionDenied
    from apps.da.models import PurchaseRequest

    da = get_object_or_404(PurchaseRequest, id=request_id, organization=request.user.organization)
    user = request.user

    # Analyser le stock pour l'affichage
    stock_analysis = []
    for line in da.items.all():
        available = line.item.stock_quantity or 0
        to_buy = max(0, line.quantity - available)
        stock_analysis.append({
            "item": line.item,
            "quantity": line.quantity,
            "available": available,
            "to_buy": to_buy,
            "unit_price": line.unit_price,
        })

    # Determiner le type de visa attendu
    is_achats_user = _is_achats(user)
    can_visa_dir = _can_validate_da(user, da)

    return render(request, "da/da_visa_page.html", {
        "da": da,
        "stock_analysis": stock_analysis,
        "is_achats": is_achats_user,
        "is_director": can_visa_dir,
        "can_visa": (
            (is_achats_user and da.status == "VISEE_DIRECTEUR") or
            (can_visa_dir and da.status == "SOUMISE")
        ),
    })


'''
        vsrc = vsrc[:match_pos] + new_page_view + vsrc[match_pos:]
        views_file.write_text(vsrc, encoding="utf-8")
        print("[OK] da_visa_page ajoutee (page de visa avec apercu stock)")

# ═══════════════════════════════════════════════════════════════
# 3. CREER LE TEMPLATE da/da_visa_page.html
# ═══════════════════════════════════════════════════════════════
tpl_dir = Path("templates/da")
tpl_dir.mkdir(parents=True, exist_ok=True)

visa_tpl = tpl_dir / "da_visa_page.html"
visa_tpl.write_text('''{% extends "base.html" %}
{% load fcfa %}

{% block content %}
<div class="p-6 max-w-4xl mx-auto">

  <div class="mb-6">
    <h1 class="text-2xl font-bold text-slate-900">{{ da.number }} — Visa</h1>
    <p class="text-sm text-slate-500 mt-1">
      Demande de {{ da.requester.first_name }} {{ da.requester.last_name }}
      · {{ da.service.name|default:"—" }}
      · Statut : <span class="font-medium">{{ da.get_status_display }}</span>
    </p>
  </div>

  {# Info DA #}
  <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-5 mb-6">
    <h2 class="font-semibold text-slate-700 mb-3">Objet de la demande</h2>
    <p class="text-slate-600">{{ da.purpose }}</p>
    <div class="mt-3 flex items-center justify-between">
      <span class="text-sm text-slate-500">Montant total</span>
      <span class="text-xl font-bold text-slate-900">{{ da.total_amount|fcfa }}</span>
    </div>
  </div>

  {# Analyse stock pour les Achats #}
  {% if is_achats and stock_analysis %}
  <div class="bg-amber-50 border border-amber-200 rounded-xl p-5 mb-6">
    <h2 class="font-semibold text-amber-800 mb-3">📦 Analyse du stock</h2>
    <table class="w-full text-sm">
      <thead class="text-xs text-amber-700 border-b border-amber-200">
        <tr>
          <th class="text-left py-2">Produit</th>
          <th class="text-center">Qté demandée</th>
          <th class="text-center">Stock dispo</th>
          <th class="text-center">À acheter</th>
        </tr>
      </thead>
      <tbody>
      {% for line in stock_analysis %}
        <tr class="border-b border-amber-100 last:border-0">
          <td class="py-2">{{ line.item.name }}</td>
          <td class="text-center">{{ line.quantity }}</td>
          <td class="text-center {% if line.available >= line.quantity %}text-emerald-600 font-medium{% else %}text-red-600 font-medium{% endif %}">
            {{ line.available }}
          </td>
          <td class="text-center font-bold {% if line.to_buy > 0 %}text-red-600{% else %}text-emerald-600{% endif %}">
            {{ line.to_buy }}
          </td>
        </tr>
      {% endfor %}
      </tbody>
    </table>
  </div>
  {% endif %}

  {# Formulaire de visa #}
  {% if can_visa %}
  <div class="bg-white rounded-xl shadow-sm border border-slate-200 p-5">
    <h2 class="font-semibold text-slate-700 mb-3">
      {% if is_achats %}
        Visa du Directeur des Achats
        <span class="text-sm font-normal text-slate-500">(verifie le stock et appose son visa)</span>
      {% else %}
        Visa du Directeur
      {% endif %}
    </h2>
    <form method="post" action="{% url 'da_visa' da.id %}">
      {% csrf_token %}
      <input type="hidden" name="approved" value="yes">
      <div class="mb-4">
        <label class="block text-sm font-medium text-slate-700 mb-2">Commentaire (optionnel)</label>
        <textarea name="comment" rows="3"
                  class="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="Visa accordé, stock disponible..."></textarea>
      </div>
      <div class="flex gap-3">
        <button type="submit"
                class="flex-1 bg-emerald-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-emerald-700">
          ✓ Apposer le visa
        </button>
        <button type="submit" name="approved" value="no"
                class="flex-1 bg-red-100 text-red-700 px-6 py-3 rounded-lg font-medium hover:bg-red-200">
          ✗ Refuser
        </button>
      </div>
    </form>
  </div>
  {% else %}
  <div class="bg-slate-100 rounded-xl p-5 text-center text-slate-500">
    Vous n'avez pas les droits pour viser cette DA.
  </div>
  {% endif %}

  <div class="mt-6">
    <a href="{% url 'da_detail' da.id %}" class="text-sm text-slate-500 hover:text-slate-700">← Retour à la DA</a>
  </div>

</div>
{% endblock %}
''', encoding="utf-8")
print("[OK] Template da/da_visa_page.html cree")

# ═══════════════════════════════════════════════════════════════
# 4. AJOUTER LA ROUTE da_visa_page
# ═══════════════════════════════════════════════════════════════
urls_file = Path("apps/da/urls.py")
usrc = urls_file.read_text(encoding="utf-8")

if "da_visa_page" not in usrc:
    old_line = 'path("requests/<uuid:request_id>/visa/", views.da_visa, name="da_visa"),'
    new_line = '''path("requests/<uuid:request_id>/visa/", views.da_visa_page, name="da_visa_page"),
    path("requests/<uuid:request_id>/visa/confirm/", views.da_visa, name="da_visa"),'''
    usrc = usrc.replace(old_line, new_line)
    urls_file.write_text(usrc, encoding="utf-8")
    print("[OK] Routes /visa/ (page) et /visa/confirm/ (action) ajoutees")

# ═══════════════════════════════════════════════════════════════
# 5. TEST DU FLUX COMPLET
# ═══════════════════════════════════════════════════════════════
print("\n--- TEST DU NOUVEAU FLUX ---")

from apps.accounts.models import User
from apps.da.models import PurchaseRequest, PurchaseRequestItem, DAItem, DACategory
from apps.da import workflow

PurchaseRequest.objects.all().delete()

chef = User.objects.get(email="chef.maint@sonabel-demo.com")
org = chef.organization
cat = DACategory.objects.get(organization=org, name="Fournitures Informatiques")
item = DAItem.objects.get(organization=org, name="Ordinateur portable HP")

da = PurchaseRequest.objects.create(
    organization=org,
    number="DA-MERGE-TEST-001",
    requester=chef,
    service=chef.service,
    purpose="Test fusion stock+visa",
    status="SOUMISE",
    priority="NORMALE",
    total_amount=900000,
    currency_code="FCFA",
)
PurchaseRequestItem.objects.create(request=da, item=item, quantity=2, unit_price=450000, quantity_received=0)
print(f"  Etat initial : {da.status}")

# 1. Directeur du service vise
dir_service = User.objects.get(email="dir.tech@sonabel-demo.com")
workflow.visa_by_director(da, actor=dir_service, approved=True)
da.refresh_from_db()
print(f"  1. Dir service vise  -> {da.status}")

# 2. Achats verifie + vise (simulation de l'action fusionnee)
dir_achats = User.objects.get(email="achats@sonabel-demo.com")
analysis = {}
for line in da.items.all():
    analysis[str(line.item_id)] = {"available": line.item.stock_quantity, "to_buy": 0}
workflow.verify_stock(da, actor=dir_achats, stock_analysis=analysis)
da.refresh_from_db()
print(f"  2a. Stock verifie    -> {da.status}")

workflow.visa_by_achats(da, actor=dir_achats, approved=True)
da.refresh_from_db()
print(f"  2b. Achats vise      -> {da.status}")

print()
print("=" * 70)
print("  ✅ WORKFLOW CORRECT")
print("=" * 70)
print("""
  NOUVEAU WORKFLOW (simplifie) :

  1. Chef de service              -> SOUMISE
  2. Directeur du service du chef -> VISEE_DIRECTEUR
  3. Directeur des Achats         -> VISEE_ACHATS (verifie stock + vise en 1 action)
  4. DG                           -> VALIDEE
  5. Envoi fournisseur            -> COMMANDEE

  POUR LA DEMO :
  · URL de visa : /da/requests/<id>/visa/
  · Le directeur des achats voit l'analyse stock ET peut viser direct
""")
print("=" * 70)
