"""PACK A1 — Import CSV membres + Emails réels."""
from pathlib import Path
ROOT = Path.cwd()

def patch(path, old, new, label):
    p = ROOT / path
    if not p.exists():
        print(f"  ✗ {path} introuvable"); return False
    src = p.read_text(encoding="utf-8")
    if old not in src:
        if new[:50] in src: print(f"  ℹ {label} déjà patché"); return True
        print(f"  ⚠ {label} : pattern introuvable"); return False
    p.write_text(src.replace(old, new, 1), encoding="utf-8")
    print(f"  ✓ {label}"); return True

def write(path, content, label):
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    print(f"  ✓ {label}")

# ═══════════════════════════════════════════════════════════════
# 1. Vue Import CSV membres
# ═══════════════════════════════════════════════════════════════
p = ROOT / "apps/accounts/views.py"
src = p.read_text(encoding="utf-8")
if "def import_members_csv" not in src:
    src += '''


# ═══════════════════════════════════════════════════════════════
# IMPORT CSV MEMBRES
# ═══════════════════════════════════════════════════════════════
from django.core.exceptions import PermissionDenied
from django.db import transaction
import csv
import io
import secrets


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
    resp.write("email,first_name,last_name,internal_id,role\\n")
    resp.write("jean.dupont@sonabel.bf,Jean,Dupont,MAT001,MEMBRE\\n")
    resp.write("marie.kone@sonabel.bf,Marie,Kone,MAT002,MEMBRE\\n")
    return resp
'''
    p.write_text(src, encoding="utf-8")
    print("  ✓ Vues import CSV")

# ═══════════════════════════════════════════════════════════════
# 2. URLs
# ═══════════════════════════════════════════════════════════════
p = ROOT / "config/urls.py"
src = p.read_text(encoding="utf-8")
if "import_members_csv" not in src:
    src = src.replace(
        "from apps.accounts.views import profile, save_theme",
        "from apps.accounts.views import (\n    profile, save_theme, import_members_page, import_members_csv, import_members_template,\n)",
    )
    src = src.replace(
        "    # Profil\n",
        '''    # Import membres RH
    path('rh/members/import/', import_members_page, name='import_members'),
    path('rh/members/import/upload/', import_members_csv, name='import_members_upload'),
    path('rh/members/import/template/', import_members_template, name='import_members_template'),

    # Profil
''',
    )
    p.write_text(src, encoding="utf-8")
    print("  ✓ URLs import CSV")

# ═══════════════════════════════════════════════════════════════
# 3. Template import_members.html
# ═══════════════════════════════════════════════════════════════
write("templates/admin/import_members.html", '''{% extends "base.html" %}
{% block title %}Importer des membres — {{ organization.name }}{% endblock %}
{% block content %}
<div class="max-w-4xl mx-auto">

    <div class="flex items-center justify-between gap-4 mb-8">
        <div class="flex items-center gap-4">
            <div class="w-12 h-12 rounded-2xl flex items-center justify-center text-white shadow-lg"
                 style="background: linear-gradient(135deg, {{ organization.color_primary|default:'#2563eb' }}, {{ organization.color_secondary|default:'#1e40af' }});">
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/></svg>
            </div>
            <div>
                <h1 class="text-3xl font-extrabold text-slate-900">Importer des membres</h1>
                <p class="text-slate-500 text-sm">Ajoutez plusieurs employés en une seule fois</p>
            </div>
        </div>
        <a href="{% url 'import_members_template' %}" class="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-white border border-slate-200 text-slate-700 text-sm font-semibold hover:bg-slate-50">
            ⬇ Télécharger le modèle
        </a>
    </div>

    {% if error %}
    <div class="mb-6 p-4 rounded-xl bg-red-50 border border-red-200 text-red-900 text-sm">{{ error }}</div>
    {% endif %}

    {% if result %}
    <div class="mb-6 grid grid-cols-3 gap-4">
        <div class="bg-emerald-50 border border-emerald-200 rounded-2xl p-4 text-center">
            <p class="text-3xl font-extrabold text-emerald-700">{{ result.created|length }}</p>
            <p class="text-sm text-emerald-700 font-semibold">Créés</p>
        </div>
        <div class="bg-amber-50 border border-amber-200 rounded-2xl p-4 text-center">
            <p class="text-3xl font-extrabold text-amber-700">{{ result.skipped|length }}</p>
            <p class="text-sm text-amber-700 font-semibold">Ignorés (existent)</p>
        </div>
        <div class="bg-red-50 border border-red-200 rounded-2xl p-4 text-center">
            <p class="text-3xl font-extrabold text-red-700">{{ result.errors|length }}</p>
            <p class="text-sm text-red-700 font-semibold">Erreurs</p>
        </div>
    </div>

    {% if result.created %}
    <div class="mb-6 bg-white rounded-2xl shadow-card border border-slate-100 overflow-hidden">
        <div class="p-4 border-b border-slate-100 flex items-center justify-between">
            <h2 class="font-bold text-slate-900">🔑 Identifiants créés</h2>
            <p class="text-xs text-slate-500">⚠️ Notez ces mots de passe — ils ne seront plus visibles</p>
        </div>
        <table class="w-full text-sm">
            <thead class="bg-slate-50">
                <tr>
                    <th class="p-3 text-left font-semibold text-slate-600">Email</th>
                    <th class="p-3 text-left font-semibold text-slate-600">Mot de passe</th>
                    <th class="p-3 text-left font-semibold text-slate-600">Matricule</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
                {% for u in result.created %}
                <tr>
                    <td class="p-3 font-mono text-xs">{{ u.email }}</td>
                    <td class="p-3 font-mono text-xs font-bold text-brand-700">{{ u.password }}</td>
                    <td class="p-3 text-xs text-slate-500">{{ u.internal_id|default:"—" }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    {% endif %}

    {% if result.errors %}
    <div class="mb-6 p-4 rounded-xl bg-red-50 border border-red-200">
        <p class="font-semibold text-red-900 mb-2">Erreurs :</p>
        <ul class="text-sm text-red-800 space-y-1 list-disc list-inside">
            {% for e in result.errors %}<li>{{ e }}</li>{% endfor %}
        </ul>
    </div>
    {% endif %}
    {% endif %}

    <form method="post" enctype="multipart/form-data" class="bg-white rounded-2xl shadow-card border border-slate-100 p-6">
        {% csrf_token %}
        <div class="border-2 border-dashed border-slate-300 rounded-2xl p-8 text-center hover:border-brand-400 transition">
            <svg class="w-12 h-12 mx-auto text-slate-400 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
            <label class="block text-sm font-medium text-slate-700 mb-2">Sélectionner un fichier CSV</label>
            <input type="file" name="csv_file" accept=".csv" required
                   class="block mx-auto text-sm file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-brand-600 file:text-white file:font-semibold hover:file:bg-brand-700">
            <p class="text-xs text-slate-500 mt-3">Format : email, first_name, last_name, internal_id, role</p>
        </div>
        <div class="flex justify-end mt-6">
            <button type="submit" class="px-6 py-3 rounded-xl bg-brand-600 text-white font-semibold hover:bg-brand-700 shadow-sm">
                Importer les membres
            </button>
        </div>
    </form>
</div>
{% endblock %}
''', "templates/admin/import_members.html")

# ═══════════════════════════════════════════════════════════════
# 4. Navbar : lien Import membres (RH/Admin)
# ═══════════════════════════════════════════════════════════════
p = ROOT / "templates/components/navbar.html"
src = p.read_text(encoding="utf-8")
if "import_members" not in src:
    src = src.replace(
        """{% if user.is_staff %}
                            <a href="/admin/" class="flex items-center gap-3 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50">
                                Admin Django
                            </a>
                            {% endif %}""",
        """{% if user.role == 'ADMIN' or user.role == 'GESTIONNAIRE' %}
                            <a href="{% url 'import_members' %}" class="flex items-center gap-3 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50">
                                Importer des membres
                            </a>
                            {% endif %}
                            {% if user.is_staff %}
                            <a href="/admin/" class="flex items-center gap-3 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50">
                                Admin Django
                            </a>
                            {% endif %}""", 1
    )
    p.write_text(src, encoding="utf-8")
    print("  ✓ Navbar : lien Import membres")

# ═══════════════════════════════════════════════════════════════
# 5. Emails — Templates HTML + Services
# ═══════════════════════════════════════════════════════════════
write("templates/emails/order_validated.html", '''<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="font-family:Inter,system-ui,sans-serif;background:#f8fafc;margin:0;padding:32px 16px">
<table width="100%"><tr><td align="center">
<table width="560" style="background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.08)">
<tr><td style="background:linear-gradient(135deg,{{ color_primary|default:'#2563eb' }},{{ color_secondary|default:'#1e40af' }});padding:32px;color:#fff">
<h1 style="margin:0;font-size:24px;font-weight:800">{{ organization.name }}</h1>
<p style="margin:8px 0 0;opacity:.9;font-size:14px">ZionPay — Achat groupé</p>
</td></tr>
<tr><td style="padding:32px">
<h2 style="margin:0 0 8px;font-size:22px;color:#0f172a">✓ Commande validée</h2>
<p style="margin:0 0 24px;color:#64748b;font-size:14px">Bonjour, votre commande est confirmée.</p>
<div style="background:#f1f5f9;border-radius:12px;padding:16px;margin-bottom:24px">
<p style="margin:0 0 8px;font-size:12px;color:#64748b;text-transform:uppercase;letter-spacing:.5px">Numéro</p>
<p style="margin:0;font-size:18px;font-weight:700;color:#0f172a">{{ order_number }}</p>
</div>
<table width="100%" style="border-collapse:collapse;margin-bottom:24px">
<tr><td style="padding:8px 0;color:#64748b;font-size:14px">Montant</td>
<td style="padding:8px 0;text-align:right;font-weight:700;color:#0f172a">{{ total_amount }} {{ currency }}</td></tr>
<tr><td style="padding:8px 0;color:#64748b;font-size:14px">Retenue salariale</td>
<td style="padding:8px 0;text-align:right;color:#10b981;font-weight:600">Automatique</td></tr>
</table>
<a href="{{ order_url }}" style="display:inline-block;background:#2563eb;color:#fff;padding:14px 24px;border-radius:12px;text-decoration:none;font-weight:600;font-size:14px">Voir ma commande →</a>
</td></tr>
<tr><td style="padding:24px;background:#f8fafc;text-align:center;font-size:12px;color:#94a3b8">
© {% now "Y" %} ZionPay — Ne pas répondre à cet email
</td></tr>
</table>
</td></tr></table>
</body></html>
''', "templates/emails/order_validated.html")

write("templates/emails/order_delivered.html", '''<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="font-family:Inter,system-ui,sans-serif;background:#f8fafc;margin:0;padding:32px 16px">
<table width="100%"><tr><td align="center">
<table width="560" style="background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.08)">
<tr><td style="background:linear-gradient(135deg,#10b981,#059669);padding:32px;color:#fff">
<h1 style="margin:0;font-size:24px;font-weight:800">{{ organization.name }}</h1>
<p style="margin:8px 0 0;opacity:.9;font-size:14px">ZionPay — Achat groupé</p>
</td></tr>
<tr><td style="padding:32px">
<h2 style="margin:0 0 8px;font-size:22px;color:#0f172a">🎉 Commande livrée</h2>
<p style="margin:0 0 24px;color:#64748b;font-size:14px">Votre commande a été livrée avec succès. Merci de votre confiance !</p>
<div style="background:#f1f5f9;border-radius:12px;padding:16px;margin-bottom:24px">
<p style="margin:0 0 8px;font-size:12px;color:#64748b;text-transform:uppercase">Numéro</p>
<p style="margin:0;font-size:18px;font-weight:700;color:#0f172a">{{ order_number }}</p>
</div>
<a href="{{ order_url }}" style="display:inline-block;background:#10b981;color:#fff;padding:14px 24px;border-radius:12px;text-decoration:none;font-weight:600;font-size:14px">Voir le détail →</a>
</td></tr>
<tr><td style="padding:24px;background:#f8fafc;text-align:center;font-size:12px;color:#94a3b8">
© {% now "Y" %} ZionPay
</td></tr>
</table>
</td></tr></table>
</body></html>
''', "templates/emails/order_delivered.html")

# ═══════════════════════════════════════════════════════════════
# 6. Service email (utilise Django mail backend)
# ═══════════════════════════════════════════════════════════════
write("apps/notifications/email_service.py", '''"""Service d'envoi d'emails HTML."""
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def send_email(recipient_email, subject, template_name, context):
    """Envoie un email HTML à partir d'un template."""
    try:
        html = render_to_string(template_name, context)
        text = strip_tags(html)
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "ZionPay <noreply@zionpay.app>")
        msg = EmailMultiAlternatives(subject, text, from_email, [recipient_email])
        msg.attach_alternative(html, "text/html")
        msg.send(fail_silently=True)
        return True
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Email send failed: {e}")
        return False


def send_order_validated_email(order):
    from django.conf import settings
    base_url = getattr(settings, "SITE_URL", "http://127.0.0.1:8000")
    return send_email(
        recipient_email=order.member.email,
        subject=f"✓ Commande {order.order_number} validée",
        template_name="emails/order_validated.html",
        context={
            "organization": order.organization,
            "color_primary": order.organization.color_primary,
            "color_secondary": order.organization.color_secondary,
            "order_number": order.order_number,
            "total_amount": f"{order.total_amount:,.0f}".replace(",", " "),
            "currency": order.currency_code,
            "order_url": f"{base_url}/orders/{order.id}/",
        },
    )


def send_order_delivered_email(order):
    from django.conf import settings
    base_url = getattr(settings, "SITE_URL", "http://127.0.0.1:8000")
    return send_email(
        recipient_email=order.member.email,
        subject=f"🎉 Commande {order.order_number} livrée",
        template_name="emails/order_delivered.html",
        context={
            "organization": order.organization,
            "order_number": order.order_number,
            "order_url": f"{base_url}/orders/{order.id}/",
        },
    )
''', "apps/notifications/email_service.py")

# ═══════════════════════════════════════════════════════════════
# 7. Brancher email_service sur les signaux
# ═══════════════════════════════════════════════════════════════
p = ROOT / "apps/notifications/signals.py"
src = p.read_text(encoding="utf-8")
if "send_order_validated_email" not in src:
    src += '''


# ═══════════════════════════════════════════════════════════════
# EMAILS HTML sur changement de statut
# ═══════════════════════════════════════════════════════════════
@receiver(post_save, sender="orders.OrderStatusHistory")
def send_email_on_status_change(sender, instance, created, **kwargs):
    """Envoie un email HTML quand le statut change."""
    if not created:
        return
    from .email_service import send_order_validated_email, send_order_delivered_email

    status = instance.to_status
    order = instance.order

    try:
        if status == "VALIDEE":
            send_order_validated_email(order)
        elif status == "LIVREE":
            send_order_delivered_email(order)
    except Exception:
        pass
'''
    p.write_text(src, encoding="utf-8")
    print("  ✓ Signals email ajoutés")

# ═══════════════════════════════════════════════════════════════
# 8. Settings — Email + SITE_URL
# ═══════════════════════════════════════════════════════════════
p = ROOT / "config/settings/base.py"
src = p.read_text(encoding="utf-8")
if "SITE_URL" not in src:
    src += '''

# ============================================================
# EMAIL & SITE
# ============================================================
SITE_URL = env("SITE_URL", default="http://127.0.0.1:8000")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="ZionPay <noreply@zionpay.app>")

# Dev = console, prod = SMTP
if DEBUG:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
else:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = env("EMAIL_HOST", default="smtp.sendgrid.net")
    EMAIL_PORT = env.int("EMAIL_PORT", default=587)
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="apikey")
    EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
'''
    p.write_text(src, encoding="utf-8")
    print("  ✓ Settings email + SITE_URL")

print()
print("=" * 60)
print("  PACK A1 TERMINÉ")
print("=" * 60)
