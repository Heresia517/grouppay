"""PACK A2 — Factures PDF + Export retenue salariale UI."""
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
# FACTURES — Modèle
# ═══════════════════════════════════════════════════════════════
p = ROOT / "apps/documents/models.py"
src = p.read_text(encoding="utf-8")
if "class InvoiceDocument" not in src:
    src += '''


class InvoiceDocument(models.Model):
    """Facture PDF liée à une commande."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(
        "orders.Order", on_delete=models.CASCADE, related_name="invoice_document",
    )
    invoice_number = models.CharField(max_length=50, unique=True)
    file = models.FileField(upload_to="invoices/", null=True, blank=True)
    file_hash = models.CharField(max_length=64, blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    downloaded_at = models.DateTimeField(null=True, blank=True)
    download_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Facture {self.invoice_number}"
'''
    p.write_text(src, encoding="utf-8")
    print("  ✓ InvoiceDocument model")

# ═══════════════════════════════════════════════════════════════
# FACTURES — Service
# ═══════════════════════════════════════════════════════════════
write("apps/documents/invoice_service.py", '''"""Service de génération de factures PDF."""
import hashlib
from datetime import date
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.utils import timezone

from apps.orders.models import Order
from .models import InvoiceDocument


def generate_invoice_number(order):
    """FAC-SONABEL-2026-000001"""
    year = order.created_at.year if order.created_at else date.today().year
    prefix = f"FAC-{order.organization.slug.upper()}-{year}-"
    count = InvoiceDocument.objects.filter(
        invoice_number__startswith=prefix
    ).count()
    return f"{prefix}{count + 1:06d}"


def generate_invoice_pdf(order):
    """Génère et stocke la facture PDF de la commande."""
    doc = InvoiceDocument.objects.filter(order=order).first()
    if doc and doc.file:
        return doc

    if not doc:
        doc = InvoiceDocument.objects.create(
            order=order,
            invoice_number=generate_invoice_number(order),
        )

    html = render_to_string("documents/invoice_pdf.html", {
        "order": order,
        "organization": order.organization,
        "member": order.member,
        "items": order.items.select_related("product").all(),
        "generated_at": timezone.now(),
        "invoice_number": doc.invoice_number,
    })

    try:
        from xhtml2pdf import pisa
        buf = BytesIO()
        result = pisa.CreatePDF(html, dest=buf, encoding="utf-8")
        if result.err:
            raise Exception(f"xhtml2pdf error: {result.err}")
        pdf_bytes = buf.getvalue()
    except ImportError:
        # Fallback : écrire le HTML comme fichier (utile si xhtml2pdf absent)
        pdf_bytes = html.encode("utf-8")

    # Save
    filename = f"{doc.invoice_number}.pdf"
    doc.file.save(filename, ContentFile(pdf_bytes), save=False)
    doc.file_hash = hashlib.sha256(pdf_bytes).hexdigest()
    doc.save(update_fields=["file", "file_hash"])
    return doc


def get_or_create_invoice(order):
    """Helper idempotent."""
    doc = InvoiceDocument.objects.filter(order=order).first()
    if doc and doc.file:
        return doc
    return generate_invoice_pdf(order)
''', "apps/documents/invoice_service.py")

# ═══════════════════════════════════════════════════════════════
# FACTURES — Vues
# ═══════════════════════════════════════════════════════════════
p = ROOT / "apps/documents/views.py"
src = p.read_text(encoding="utf-8")
if "def preview_invoice_html" not in src:
    src += '''


# ═══════════════════════════════════════════════════════════════
# FACTURES
# ═══════════════════════════════════════════════════════════════
@login_required
def preview_invoice_html(request, order_id):
    """Aperçu HTML stylé de la facture."""
    order = get_object_or_404(Order, id=order_id)
    if not _check_permission(request, order):
        raise Http404("Commande introuvable")

    from .invoice_service import get_or_create_invoice
    doc = get_or_create_invoice(order)

    return render(request, "documents/invoice.html", {
        "order": order,
        "items": order.items.select_related("product").all(),
        "invoice": doc,
    })


@login_required
def preview_invoice_pdf(request, order_id):
    """Affiche le PDF facture inline."""
    order = get_object_or_404(Order, id=order_id)
    if not _check_permission(request, order):
        raise Http404

    from .invoice_service import get_or_create_invoice
    doc = get_or_create_invoice(order)

    return FileResponse(doc.file.open("rb"), content_type="application/pdf", as_attachment=False)


@login_required
def download_invoice_pdf(request, order_id):
    """Force le téléchargement de la facture."""
    order = get_object_or_404(Order, id=order_id)
    if not _check_permission(request, order):
        raise Http404

    from .invoice_service import get_or_create_invoice
    from django.utils import timezone
    doc = get_or_create_invoice(order)

    # Tracker le download
    doc.downloaded_at = timezone.now()
    doc.download_count = (doc.download_count or 0) + 1
    doc.save(update_fields=["downloaded_at", "download_count"])

    return FileResponse(
        doc.file.open("rb"),
        as_attachment=True,
        filename=f"{doc.invoice_number}.pdf",
    )
'''
    p.write_text(src, encoding="utf-8")
    print("  ✓ Vues factures")

# ═══════════════════════════════════════════════════════════════
# EXPORT RETENUE — Vues
# ═══════════════════════════════════════════════════════════════
write("apps/deductions/views.py", '''"""Vues retenue salariale — dashboard + preview + download."""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Sum, Count
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import DeductionTransmission, DeductionExportBatch


def _require_rh(user):
    if user.role not in ("ADMIN", "GESTIONNAIRE"):
        raise PermissionDenied("Réservé RH/Admin")


@login_required
def deductions_dashboard(request):
    """Dashboard retenue salariale."""
    _require_rh(request.user)
    org = request.user.organization

    # KPIs
    pending = DeductionTransmission.objects.filter(organization=org, status="EN_ATTENTE")
    sent = DeductionTransmission.objects.filter(organization=org, status="ENVOYEE")
    confirmed = DeductionTransmission.objects.filter(organization=org, status="CONFIRMEE")

    # Période par défaut : mois courant
    today = date.today()
    period_start = request.GET.get("start", today.replace(day=1).isoformat())
    period_end = request.GET.get("end", today.isoformat())

    try:
        start_d = date.fromisoformat(period_start)
        end_d = date.fromisoformat(period_end)
    except ValueError:
        start_d = today.replace(day=1)
        end_d = today
        period_start, period_end = start_d.isoformat(), end_d.isoformat()

    # Transmissions dans la période
    in_period = pending.filter(
        created_at__date__gte=start_d,
        created_at__date__lte=end_d,
    )

    # Historique
    batches = DeductionExportBatch.objects.filter(
        organization=org
    ).order_by("-created_at")[:20]

    context = {
        "kpis": {
            "pending_count": pending.count(),
            "pending_amount": pending.aggregate(s=Sum("amount"))["s"] or 0,
            "sent_count": sent.count(),
            "confirmed_count": confirmed.count(),
            "confirmed_amount": confirmed.aggregate(s=Sum("amount"))["s"] or 0,
            "period_count": in_period.count(),
            "period_amount": in_period.aggregate(s=Sum("amount"))["s"] or 0,
        },
        "period_start": period_start,
        "period_end": period_end,
        "transmissions": in_period.select_related("order", "order__member")[:100],
        "batches": batches,
    }
    return render(request, "deductions/dashboard.html", context)


@login_required
def preview_export(request):
    """Aperçu HTML du CSV avant génération (AJAX/HTMX)."""
    _require_rh(request.user)
    org = request.user.organization

    start = request.GET.get("start")
    end = request.GET.get("end")

    try:
        start_d = date.fromisoformat(start)
        end_d = date.fromisoformat(end)
    except (ValueError, TypeError):
        return JsonResponse({"error": "Dates invalides"}, status=400)

    qs = DeductionTransmission.objects.filter(
        organization=org,
        status="EN_ATTENTE",
        created_at__date__gte=start_d,
        created_at__date__lte=end_d,
    ).select_related("order", "order__member")

    rows = [
        {
            "internal_id": t.member_internal_id or "—",
            "email": t.member_email,
            "order_number": t.order.order_number,
            "reference": t.reference,
            "amount": float(t.amount or 0),
            "currency": t.currency_code or org.currency_code,
        }
        for t in qs
    ]

    total = sum(r["amount"] for r in rows)

    return render(request, "deductions/_preview.html", {
        "rows": rows,
        "total": total,
        "count": len(rows),
        "start": start,
        "end": end,
        "currency": org.currency_code,
    })


@login_required
@require_POST
def generate_export(request):
    """Génère le CSV et redirige vers le dashboard."""
    _require_rh(request.user)
    org = request.user.organization

    start = request.POST.get("start")
    end = request.POST.get("end")

    try:
        start_d = date.fromisoformat(start)
        end_d = date.fromisoformat(end)
    except (ValueError, TypeError):
        return redirect("deductions_dashboard")

    # Appel du service existant
    from .services import generate_export_batch

    try:
        batch = generate_export_batch(
            organization=org,
            period_start=start_d,
            period_end=end_d,
            user=request.user,
        )
        if batch:
            return redirect("deductions_dashboard")
    except TypeError:
        # Signature différente — fallback
        try:
            batch = generate_export_batch(org, start_d, end_d, request.user)
            if batch:
                return redirect("deductions_dashboard")
        except Exception:
            pass
    except Exception as e:
        pass

    return redirect("deductions_dashboard")


@login_required
def download_batch(request, batch_id):
    """Télécharge un batch CSV existant."""
    _require_rh(request.user)
    batch = get_object_or_404(
        DeductionExportBatch, id=batch_id, organization=request.user.organization,
    )
    if not batch.file:
        return HttpResponse("Fichier introuvable", status=404)

    from django.utils import timezone
    if not batch.downloaded_at:
        batch.downloaded_at = timezone.now()
        batch.save(update_fields=["downloaded_at"])

    filename = f"retenue-{batch.organization.slug}-{batch.period_start}-{batch.period_end}.csv"
    return FileResponse(
        batch.file.open("rb"),
        as_attachment=True,
        filename=filename,
    )


@login_required
@require_POST
def mark_batch_sent(request, batch_id):
    """Marque toutes les transmissions d'un batch comme ENVOYEE."""
    _require_rh(request.user)
    batch = get_object_or_404(
        DeductionExportBatch, id=batch_id, organization=request.user.organization,
    )
    updated = DeductionTransmission.objects.filter(export_batch=batch).update(status="ENVOYEE")
    return JsonResponse({"ok": True, "updated": updated})


from django.http import FileResponse  # noqa
''', "apps/deductions/views.py")

# ═══════════════════════════════════════════════════════════════
# URLS
# ═══════════════════════════════════════════════════════════════
p = ROOT / "config/urls.py"
src = p.read_text(encoding="utf-8")

if "preview_invoice_html" not in src:
    # Import
    src = src.replace(
        "from apps.documents.views import (\n    download_purchase_order_pdf, preview_purchase_order_pdf, preview_order_html,\n)",
        "from apps.documents.views import (\n    download_purchase_order_pdf, preview_purchase_order_pdf, preview_order_html,\n    preview_invoice_html, preview_invoice_pdf, download_invoice_pdf,\n)",
    )
    # URLs factures après PDF
    src = src.replace(
        "    path('orders/<uuid:order_id>/preview/', preview_order_html, name='preview_order_html'),",
        "    path('orders/<uuid:order_id>/preview/', preview_order_html, name='preview_order_html'),\n    path('orders/<uuid:order_id>/invoice/', preview_invoice_html, name='preview_invoice_html'),\n    path('orders/<uuid:order_id>/invoice/pdf/', download_invoice_pdf, name='download_invoice_pdf'),\n    path('orders/<uuid:order_id>/invoice/pdf/preview/', preview_invoice_pdf, name='preview_invoice_pdf'),",
    )
    print("  ✓ URLs factures")

if "deductions_dashboard" not in src:
    src = src.replace(
        "from apps.orders.dashboard_views import rh_dashboard, bulk_validate_orders, bulk_reject_orders",
        "from apps.orders.dashboard_views import rh_dashboard, bulk_validate_orders, bulk_reject_orders\nfrom apps.deductions.views import (\n    deductions_dashboard, preview_export, generate_export, download_batch, mark_batch_sent,\n)",
    )
    src = src.replace(
        "    path('rh/dashboard/export-pdf/', export_dashboard_pdf, name='export_dashboard_pdf'),",
        '''    path('rh/dashboard/export-pdf/', export_dashboard_pdf, name='export_dashboard_pdf'),

    # Retenue salariale
    path('rh/deductions/', deductions_dashboard, name='deductions_dashboard'),
    path('rh/deductions/preview/', preview_export, name='preview_export'),
    path('rh/deductions/generate/', generate_export, name='generate_export'),
    path('rh/deductions/batch/<uuid:batch_id>/download/', download_batch, name='download_batch'),
    path('rh/deductions/batch/<uuid:batch_id>/sent/', mark_batch_sent, name='mark_batch_sent'),''',
    )
    print("  ✓ URLs retenue")

p.write_text(src, encoding="utf-8")

# ═══════════════════════════════════════════════════════════════
# TEMPLATES — Facture HTML
# ═══════════════════════════════════════════════════════════════
write("templates/documents/invoice.html", '''{% extends "base.html" %}
{% block title %}Facture {{ invoice.invoice_number }}{% endblock %}
{% block content %}
<div class="max-w-4xl mx-auto">

    <div class="flex flex-wrap items-center justify-between gap-3 mb-6 print:hidden">
        <a href="{% url 'order_detail' order.id %}" class="text-sm text-slate-600 hover:text-brand-600">← Retour à la commande</a>
        <div class="flex gap-2">
            <button onclick="window.print()" class="px-4 py-2.5 rounded-xl bg-white border border-slate-200 text-sm font-semibold">🖨️ Imprimer</button>
            <a href="{% url 'preview_invoice_pdf' order.id %}" target="_blank" class="px-4 py-2.5 rounded-xl bg-white border border-slate-200 text-sm font-semibold">👁️ PDF</a>
            <a href="{% url 'download_invoice_pdf' order.id %}" class="px-4 py-2.5 rounded-xl bg-brand-600 text-white text-sm font-semibold">⬇️ Télécharger</a>
        </div>
    </div>

    <div class="bg-white rounded-2xl shadow-card border border-slate-100 p-8 print:shadow-none print:border-none" id="invoice-preview">

        <div class="flex items-start justify-between pb-6 border-b-2 border-brand-600">
            <div>
                <h1 class="text-2xl font-extrabold text-slate-900">{{ organization.name }}</h1>
                <p class="text-xs text-slate-500 mt-1">{{ organization.country_code }} · {{ organization.currency_code }}</p>
            </div>
            <div class="text-right">
                <p class="text-xs text-slate-500 uppercase tracking-wide">Facture N°</p>
                <p class="font-bold text-lg text-slate-900">{{ invoice.invoice_number }}</p>
                <p class="text-xs text-slate-500 mt-1">Émise le {{ invoice.generated_at|date:"d/m/Y" }}</p>
            </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 py-6 border-b border-slate-100">
            <div>
                <p class="text-xs text-slate-500 uppercase tracking-wide mb-1">Client</p>
                <p class="font-medium text-slate-900">{{ member.email }}</p>
                {% if member.internal_id %}<p class="text-sm text-slate-500">Matricule : {{ member.internal_id }}</p>{% endif %}
                {% if member.first_name or member.last_name %}<p class="text-sm text-slate-500">{{ member.first_name }} {{ member.last_name }}</p>{% endif %}
            </div>
            <div>
                <p class="text-xs text-slate-500 uppercase tracking-wide mb-1">Commande liée</p>
                <p class="font-medium text-slate-900">{{ order.order_number }}</p>
                <p class="text-sm text-slate-500">Passée le {{ order.created_at|date:"d/m/Y à H:i" }}</p>
            </div>
            <div class="md:col-span-2">
                <p class="text-xs text-slate-500 uppercase tracking-wide mb-1">Adresse de livraison</p>
                <p class="text-sm text-slate-900">{{ order.delivery_address }}</p>
            </div>
        </div>

        <table class="w-full mt-6">
            <thead>
                <tr class="border-b border-slate-200">
                    <th class="text-left py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Désignation</th>
                    <th class="text-center py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Qté</th>
                    <th class="text-right py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">P.U. TTC</th>
                    <th class="text-right py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Montant</th>
                </tr>
            </thead>
            <tbody>
                {% for item in items %}
                <tr class="border-b border-slate-100">
                    <td class="py-3 text-sm text-slate-900">{{ item.product.name }}</td>
                    <td class="py-3 text-sm text-center">{{ item.quantity }}</td>
                    <td class="py-3 text-sm text-right text-slate-700">{{ item.unit_price|floatformat:0 }}</td>
                    <td class="py-3 text-sm text-right font-medium text-slate-900">{% widthratio item.unit_price 1 item.quantity %} {{ order.currency_code }}</td>
                </tr>
                {% endfor %}
            </tbody>
            <tfoot>
                <tr class="border-t-2 border-slate-900">
                    <td colspan="3" class="text-right py-4 font-bold text-slate-900 uppercase text-sm">Total TTC</td>
                    <td class="text-right py-4 font-extrabold text-lg text-slate-900">{{ order.total_amount|floatformat:0 }} {{ order.currency_code }}</td>
                </tr>
            </tfoot>
        </table>

        <div class="mt-8 pt-6 border-t border-slate-200">
            <p class="text-xs text-slate-500 leading-relaxed">
                <strong>Mode de règlement :</strong> Retenue salariale automatique — le montant sera prélevé sur le salaire du membre conformément à l'accord de mutuelle.<br>
                <strong>Mention légale :</strong> Facture émise par ZionPay pour {{ organization.name }}. Pas de TVA applicable (retenue salariale).
            </p>
            <p class="text-xs text-slate-400 text-center mt-6">
                Document généré le {% now "d/m/Y à H:i" %} · ZionPay
            </p>
        </div>
    </div>
</div>

<style media="print">
    nav, footer, .print\\:hidden, button { display: none !important; }
    body { background: white !important; }
    main { padding: 0 !important; max-width: 100% !important; }
    #invoice-preview { box-shadow: none !important; border: none !important; padding: 20px !important; }
    @page { margin: 15mm; }
</style>
{% endblock %}
''', "templates/documents/invoice.html")

# ═══════════════════════════════════════════════════════════════
# TEMPLATES — Facture PDF
# ═══════════════════════════════════════════════════════════════
write("templates/documents/invoice_pdf.html", '''<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
    @page { size: A4; margin: 15mm; }
    body { font-family: Helvetica, sans-serif; font-size: 10pt; color: #0f172a; }
    h1 { color: #1e3a8a; font-size: 20pt; margin: 0; }
    .subtitle { color: #64748b; font-size: 9pt; }
    .header { border-bottom: 2pt solid #2563eb; padding-bottom: 8pt; margin-bottom: 12pt; }
    .invoice-num { text-align: right; }
    .invoice-num .label { font-size: 8pt; color: #64748b; text-transform: uppercase; }
    .invoice-num .value { font-size: 13pt; font-weight: bold; color: #0f172a; }
    .info-block { margin-bottom: 15pt; }
    .info-block td { vertical-align: top; padding-right: 20pt; }
    .info-label { font-size: 8pt; color: #64748b; text-transform: uppercase; margin-bottom: 3pt; }
    .info-value { font-size: 10pt; color: #0f172a; }
    table.items { width: 100%; border-collapse: collapse; margin-top: 15pt; }
    table.items th { background: #2563eb; color: white; padding: 6pt; text-align: left; font-size: 8pt; text-transform: uppercase; }
    table.items td { padding: 6pt; border-bottom: 0.5pt solid #e2e8f0; font-size: 9pt; }
    table.items tfoot td { border-top: 1.5pt solid #0f172a; padding-top: 10pt; font-weight: bold; }
    .totals { text-align: right; font-size: 14pt; font-weight: bold; color: #0f172a; }
    .footer { margin-top: 30pt; padding-top: 10pt; border-top: 0.5pt solid #e2e8f0; font-size: 8pt; color: #64748b; }
</style>
</head>
<body>
    <div class="header">
        <table width="100%">
            <tr>
                <td>
                    <h1>{{ organization.name }}</h1>
                    <div class="subtitle">{{ organization.country_code }} · {{ organization.currency_code }}</div>
                </td>
                <td class="invoice-num">
                    <div class="label">Facture N°</div>
                    <div class="value">{{ invoice_number }}</div>
                    <div class="subtitle">Emise le {{ generated_at|date:"d/m/Y" }}</div>
                </td>
            </tr>
        </table>
    </div>

    <table class="info-block" width="100%">
        <tr>
            <td>
                <div class="info-label">Client</div>
                <div class="info-value">{{ member.email }}</div>
                {% if member.internal_id %}<div class="subtitle">Matricule : {{ member.internal_id }}</div>{% endif %}
                {% if member.first_name or member.last_name %}<div class="subtitle">{{ member.first_name }} {{ member.last_name }}</div>{% endif %}
            </td>
            <td>
                <div class="info-label">Commande</div>
                <div class="info-value">{{ order.order_number }}</div>
                <div class="subtitle">Passee le {{ order.created_at|date:"d/m/Y" }}</div>
            </td>
        </tr>
        <tr>
            <td colspan="2">
                <div class="info-label">Adresse de livraison</div>
                <div class="info-value">{{ order.delivery_address }}</div>
            </td>
        </tr>
    </table>

    <table class="items">
        <thead>
            <tr>
                <th>Designation</th>
                <th style="text-align:center">Qte</th>
                <th style="text-align:right">P.U. TTC</th>
                <th style="text-align:right">Montant</th>
            </tr>
        </thead>
        <tbody>
            {% for item in items %}
            <tr>
                <td>{{ item.product.name }}</td>
                <td style="text-align:center">{{ item.quantity }}</td>
                <td style="text-align:right">{{ item.unit_price|floatformat:0 }}</td>
                <td style="text-align:right">{% widthratio item.unit_price 1 item.quantity %} {{ order.currency_code }}</td>
            </tr>
            {% endfor %}
        </tbody>
        <tfoot>
            <tr>
                <td colspan="3" style="text-align:right">TOTAL TTC</td>
                <td class="totals">{{ order.total_amount|floatformat:0 }} {{ order.currency_code }}</td>
            </tr>
        </tfoot>
    </table>

    <div class="footer">
        <strong>Mode de reglement :</strong> Retenue salariale automatique.<br>
        <strong>Mention legale :</strong> Facture emise par ZionPay pour {{ organization.name }}. Pas de TVA applicable.<br>
        <div style="text-align:center; margin-top:10pt; color:#94a3b8;">Document genere par ZionPay</div>
    </div>
</body>
</html>
''', "templates/documents/invoice_pdf.html")

# ═══════════════════════════════════════════════════════════════
# DASHBOARD RETENUE
# ═══════════════════════════════════════════════════════════════
write("templates/deductions/dashboard.html", '''{% extends "base.html" %}
{% block title %}Retenue salariale — {{ organization.name }}{% endblock %}
{% block content %}
<div class="max-w-7xl mx-auto">

    <div class="flex items-center justify-between gap-4 mb-8">
        <div class="flex items-center gap-4">
            <div class="w-12 h-12 rounded-2xl flex items-center justify-center text-white shadow-lg"
                 style="background: linear-gradient(135deg, {{ organization.color_primary|default:'#2563eb' }}, {{ organization.color_secondary|default:'#1e40af' }});">
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1"/></svg>
            </div>
            <div>
                <h1 class="text-3xl font-extrabold text-slate-900">Retenue salariale</h1>
                <p class="text-slate-500 text-sm">Génération et suivi des exports pour la paie</p>
            </div>
        </div>
        <a href="{% url 'rh_dashboard' %}" class="text-sm text-slate-600 hover:text-brand-600">← Dashboard</a>
    </div>

    <!-- KPIs -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div class="bg-white rounded-2xl shadow-card border border-slate-100 p-5">
            <p class="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">En attente</p>
            <p class="text-2xl font-extrabold text-slate-900 tabular-nums">{{ kpis.pending_count }}</p>
            <p class="text-xs text-slate-500 mt-0.5">{{ kpis.pending_amount|floatformat:0 }} {{ organization.currency_code }}</p>
        </div>
        <div class="bg-white rounded-2xl shadow-card border border-slate-100 p-5">
            <p class="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Envoyées</p>
            <p class="text-2xl font-extrabold text-blue-600">{{ kpis.sent_count }}</p>
        </div>
        <div class="bg-white rounded-2xl shadow-card border border-slate-100 p-5">
            <p class="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Confirmées</p>
            <p class="text-2xl font-extrabold text-emerald-600">{{ kpis.confirmed_count }}</p>
            <p class="text-xs text-slate-500 mt-0.5">{{ kpis.confirmed_amount|floatformat:0 }} {{ organization.currency_code }}</p>
        </div>
        <div class="bg-gradient-to-br from-brand-500 to-brand-700 rounded-2xl shadow-card p-5 text-white">
            <p class="text-xs font-semibold uppercase tracking-wide mb-1 opacity-90">Période</p>
            <p class="text-2xl font-extrabold tabular-nums">{{ kpis.period_count }}</p>
            <p class="text-xs opacity-90 mt-0.5">{{ kpis.period_amount|floatformat:0 }} {{ organization.currency_code }}</p>
        </div>
    </div>

    <!-- Sélecteur de période + aperçu -->
    <div class="bg-white rounded-2xl shadow-card border border-slate-100 p-6 mb-6">
        <h2 class="font-bold text-slate-900 mb-4">Générer un nouvel export</h2>

        <div class="flex flex-wrap items-end gap-3 mb-4">
            <div>
                <label class="block text-xs font-semibold text-slate-500 uppercase mb-1">Du</label>
                <input type="date" id="period-start" value="{{ period_start }}"
                       class="rounded-lg border border-slate-200 px-3 py-2 text-sm">
            </div>
            <div>
                <label class="block text-xs font-semibold text-slate-500 uppercase mb-1">Au</label>
                <input type="date" id="period-end" value="{{ period_end }}"
                       class="rounded-lg border border-slate-200 px-3 py-2 text-sm">
            </div>
            <button type="button" onclick="previewPeriod()" class="px-4 py-2 rounded-lg bg-slate-900 text-white text-sm font-semibold hover:bg-slate-800">
                🔍 Aperçu
            </button>
        </div>

        <div id="preview-container" class="text-sm text-slate-500">
            Cliquez sur "Aperçu" pour visualiser les transmissions de la période.
        </div>

        <form method="post" action="{% url 'generate_export' %}" id="generate-form" class="mt-4 flex justify-end gap-2">
            {% csrf_token %}
            <input type="hidden" name="start" id="form-start" value="{{ period_start }}">
            <input type="hidden" name="end" id="form-end" value="{{ period_end }}">
            <button type="submit" id="generate-btn" class="px-6 py-3 rounded-xl bg-brand-600 text-white font-semibold hover:bg-brand-700 shadow-sm disabled:opacity-50">
                📥 Générer le CSV pour la paie
            </button>
        </form>
    </div>

    <!-- Historique des batchs -->
    <div class="bg-white rounded-2xl shadow-card border border-slate-100 overflow-hidden">
        <div class="p-6 border-b border-slate-100">
            <h2 class="font-bold text-slate-900">Historique des exports</h2>
            <p class="text-xs text-slate-500 mt-0.5">{{ batches|length }} batch{{ batches|length|pluralize }}</p>
        </div>

        {% if batches %}
        <table class="w-full text-sm">
            <thead class="bg-slate-50">
                <tr>
                    <th class="p-3 text-left font-semibold text-slate-600">Période</th>
                    <th class="p-3 text-left font-semibold text-slate-600">Lignes</th>
                    <th class="p-3 text-left font-semibold text-slate-600">Généré le</th>
                    <th class="p-3 text-center font-semibold text-slate-600">Actions</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
                {% for b in batches %}
                <tr>
                    <td class="p-3">{{ b.period_start|date:"d/m/Y" }} → {{ b.period_end|date:"d/m/Y" }}</td>
                    <td class="p-3 font-semibold">{{ b.row_count }}</td>
                    <td class="p-3 text-slate-500">{{ b.created_at|date:"d/m/Y H:i" }}</td>
                    <td class="p-3 text-center">
                        {% if b.file %}
                        <a href="{% url 'download_batch' b.id %}" class="inline-block px-3 py-1.5 rounded-lg bg-brand-600 text-white text-xs font-semibold hover:bg-brand-700">📥 CSV</a>
                        {% else %}<span class="text-slate-400 text-xs">Pas de fichier</span>{% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <div class="p-12 text-center">
            <div class="inline-flex items-center justify-center w-16 h-16 rounded-full bg-slate-100 mb-4">
                <svg class="w-8 h-8 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
            </div>
            <p class="text-slate-500">Aucun export généré pour le moment</p>
        </div>
        {% endif %}
    </div>
</div>

<script>
async function previewPeriod() {
    const start = document.getElementById('period-start').value;
    const end = document.getElementById('period-end').value;
    document.getElementById('form-start').value = start;
    document.getElementById('form-end').value = end;

    const container = document.getElementById('preview-container');
    container.innerHTML = '<p class="text-slate-500">Chargement...</p>';

    try {
        const r = await fetch(`{% url 'preview_export' %}?start=${start}&end=${end}`);
        if (!r.ok) throw new Error('Erreur');
        container.innerHTML = await r.text();
    } catch (e) {
        container.innerHTML = '<p class="text-red-600">Erreur de chargement</p>';
    }
}
</script>
{% endblock %}
''', "templates/deductions/dashboard.html")

write("templates/deductions/_preview.html", '''{% if rows %}
<div class="overflow-x-auto rounded-xl border border-slate-200">
    <table class="w-full text-sm">
        <thead class="bg-slate-50">
            <tr>
                <th class="p-2 text-left text-xs font-semibold text-slate-600">Matricule</th>
                <th class="p-2 text-left text-xs font-semibold text-slate-600">Email</th>
                <th class="p-2 text-left text-xs font-semibold text-slate-600">Réf. commande</th>
                <th class="p-2 text-right text-xs font-semibold text-slate-600">Montant</th>
            </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
            {% for r in rows %}
            <tr>
                <td class="p-2 font-mono text-xs">{{ r.internal_id }}</td>
                <td class="p-2 text-xs">{{ r.email }}</td>
                <td class="p-2 text-xs text-slate-500">{{ r.order_number }}</td>
                <td class="p-2 text-right font-semibold text-xs">{{ r.amount|floatformat:0 }} {{ r.currency }}</td>
            </tr>
            {% endfor %}
        </tbody>
        <tfoot class="bg-slate-900 text-white">
            <tr>
                <td colspan="3" class="p-2 text-right font-bold text-sm">TOTAL ({{ count }} ligne{{ count|pluralize }})</td>
                <td class="p-2 text-right font-extrabold">{{ total|floatformat:0 }} {{ currency }}</td>
            </tr>
        </tfoot>
    </table>
</div>
{% else %}
<div class="p-8 text-center bg-amber-50 border border-amber-200 rounded-xl">
    <p class="text-sm text-amber-800">Aucune transmission en attente sur cette période.</p>
</div>
{% endif %}
''', "templates/deductions/_preview.html")

# ═══════════════════════════════════════════════════════════════
# BOUTON facture dans order_detail
# ═══════════════════════════════════════════════════════════════
p = ROOT / "templates/orders/order_detail.html"
src = p.read_text(encoding="utf-8")
if "preview_invoice_html" not in src:
    # Chercher le bloc des boutons Aperçu/PDF/Télécharger
    old_pattern = '<a href="{% url \'preview_order_html\' order.id %}"'
    if old_pattern in src:
        # Ajouter le bouton facture avant
        src = src.replace(
            '<div class="flex flex-wrap gap-2">',
            '''<div class="flex flex-wrap gap-2">
            <a href="{% url 'preview_invoice_html' order.id %}"
               class="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-amber-500 text-white text-sm font-semibold hover:bg-amber-600 shadow-sm transition">
                🧾 Facture
            </a>''',
            1,
        )
        p.write_text(src, encoding="utf-8")
        print("  ✓ Bouton Facture dans order_detail")

# ═══════════════════════════════════════════════════════════════
# Navbar : lien Retenue (RH)
# ═══════════════════════════════════════════════════════════════
p = ROOT / "templates/components/navbar.html"
src = p.read_text(encoding="utf-8")
if "url 'deductions_dashboard'" not in src:
    # Ajouter dans le dropdown user après "Importer des membres"
    old = """{% if user.role == 'ADMIN' or user.role == 'GESTIONNAIRE' %}
                            <a href="{% url 'import_members' %}" class="flex items-center gap-3 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/></svg>
                                Importer des membres
                            </a>
                            {% endif %}"""
    new = """{% if user.role == 'ADMIN' or user.role == 'GESTIONNAIRE' %}
                            <a href="{% url 'import_members' %}" class="flex items-center gap-3 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/></svg>
                                Importer des membres
                            </a>
                            <a href="{% url 'deductions_dashboard' %}" class="flex items-center gap-3 px-4 py-2 text-sm text-slate-700 hover:bg-slate-50">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1"/></svg>
                                Retenue salariale
                            </a>
                            {% endif %}"""
    if old in src:
        src = src.replace(old, new, 1)
        p.write_text(src, encoding="utf-8")
        print("  ✓ Navbar : lien Retenue salariale")

print()
print("=" * 60)
print("  PACK A2 TERMINÉ")
print("=" * 60)
