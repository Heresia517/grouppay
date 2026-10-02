from django.shortcuts import render

# Create your views here.



from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json


@login_required
def profile(request):
    from apps.orders.models import Order
    orders = Order.objects.filter(member=request.user).order_by("-created_at")
    valid = ["VALIDEE", "EN_LIVRAISON", "LIVREE"]
    total_spent = orders.filter(status__in=valid).aggregate(s=Sum("total_amount"))["s"] or 0
    return render(request, "accounts/profile.html", {
        "stats": {
            "total_orders": orders.count(),
            "total_spent": total_spent,
            "delivered": orders.filter(status="LIVREE").count(),
            "pending": orders.filter(status="EN_ATTENTE_VALIDATION").count(),
            "savings": float(total_spent) * 0.15,
        },
        "recent_orders": orders[:5],
    })


@login_required
@require_POST
def save_theme(request):
    try:
        data = json.loads(request.body)
        theme = data.get("theme", "light")
        if theme not in ("light", "dark"):
            return JsonResponse({"error": "invalid"}, status=400)
        request.user.theme_preference = theme
        request.user.save(update_fields=["theme_preference"])
        return JsonResponse({"ok": True})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)



# ═══════════════════════════════════════════════════════════════
# IMPORT CSV MEMBRES
# ═══════════════════════════════════════════════════════════════
from django.core.exceptions import PermissionDenied
from django.db import transaction
import csv
import io
import secrets
from .models import User


def _require_rh(user):
    if user.role not in ("ADMIN", "GESTIONNAIRE"):
        raise PermissionDenied("Réservé RH/Admin")


@login_required
def import_members_page(request):
    """Affiche le formulaire d'import CSV."""
    _require_rh(request.user)
    return render(request, "admin/import_members.html", {
        "result": getattr(request, "_import_result", None),
    })


@login_required
@require_POST
def import_members_csv(request):
    """Traite le fichier CSV uploadé."""
    _require_rh(request.user)

    if "csv_file" not in request.FILES:
        return render(request, "admin/import_members.html", {
            "error": "Aucun fichier sélectionné.",
        })

    f = request.FILES["csv_file"]
    if not f.name.lower().endswith(".csv"):
        return render(request, "admin/import_members.html", {
            "error": "Le fichier doit être un .csv",
        })

    try:
        content = f.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        return render(request, "admin/import_members.html", {
            "error": "Encodage invalide — utilisez UTF-8.",
        })

    reader = csv.DictReader(io.StringIO(content))
    required_cols = {"email"}
    if not required_cols.issubset(set(reader.fieldnames or [])):
        return render(request, "admin/import_members.html", {
            "error": f"Colonnes requises : {', '.join(required_cols)}. Trouvé : {reader.fieldnames}",
        })

    created, skipped, errors = [], [], []
    org = request.user.organization

    for i, row in enumerate(reader, start=2):
        email = (row.get("email") or "").strip().lower()
        if not email:
            errors.append(f"Ligne {i} : email vide")
            continue

        if User.objects.filter(organization=org, email=email).exists():
            skipped.append(email)
            continue

        password = secrets.token_urlsafe(10)
        try:
            with transaction.atomic():
                u = User.objects.create_user(
                    email=email,
                    organization=org,
                    password=password,
                    role=row.get("role", "MEMBRE").strip().upper() or "MEMBRE",
                    internal_id=(row.get("internal_id") or "").strip(),
                    first_name=(row.get("first_name") or "").strip(),
                    last_name=(row.get("last_name") or "").strip(),
                )
            created.append({"email": email, "password": password, "internal_id": u.internal_id})
        except Exception as e:
            errors.append(f"Ligne {i} ({email}) : {e}")

    return render(request, "admin/import_members.html", {
        "result": {
            "created": created,
            "skipped": skipped,
            "errors": errors,
            "total": len(created) + len(skipped) + len(errors),
        },
    })


@login_required
def import_members_template(request):
    """Télécharge un CSV modèle."""
    _require_rh(request.user)
    from django.http import HttpResponse
    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = 'attachment; filename="modele-membres.csv"'
    resp.write("email,first_name,last_name,internal_id,role\n")
    resp.write("jean.dupont@sonabel.bf,Jean,Dupont,MAT001,MEMBRE\n")
    resp.write("marie.kone@sonabel.bf,Marie,Kone,MAT002,MEMBRE\n")
    return resp
