"""Vues pour les rapports mensuels."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import MonthlyReport
from .report_service import generate_report, send_report_email


def _require_rh(user):
    if user.role not in ("ADMIN", "GESTIONNAIRE") and not user.is_dg:
        raise PermissionDenied("Reserve RH/DG")


@login_required
def reports_list(request):
    """Liste des rapports mensuels."""
    _require_rh(request.user)
    org = request.user.organization

    reports = MonthlyReport.objects.filter(organization=org).order_by("-year", "-month")

    return render(request, "reports/list.html", {"reports": reports})


@login_required
@require_POST
def report_generate(request):
    """Genere le rapport du mois precedent."""
    _require_rh(request.user)
    org = request.user.organization

    now = timezone.now()
    year = now.year
    month = now.month - 1
    if month == 0:
        month = 12
        year -= 1

    results = generate_report(year=year, month=month, organization=org)
    result = results[0] if results else None

    if result and result["status"] == "OK":
        messages.success(request, f"Rapport {month:02d}/{year} genere avec succes")
    else:
        messages.error(request, f"Erreur : {result.get('error', 'inconnue') if result else 'inconnue'}")

    return redirect("reports_list")


@login_required
@require_POST
def report_regenerate(request, report_id):
    """Regenere un rapport existant."""
    _require_rh(request.user)
    report = get_object_or_404(MonthlyReport, id=report_id, organization=request.user.organization)

    results = generate_report(year=report.year, month=report.month, organization=report.organization)
    result = results[0] if results else None

    if result and result["status"] == "OK":
        messages.success(request, f"Rapport {report.period_label} regenere")
    else:
        messages.error(request, "Erreur de regeneration")

    return redirect("reports_list")


@login_required
def report_download_pdf(request, report_id):
    """Telecharge le PDF."""
    _require_rh(request.user)
    report = get_object_or_404(MonthlyReport, id=report_id, organization=request.user.organization)

    if not report.pdf_file:
        messages.error(request, "PDF non disponible")
        return redirect("reports_list")

    return FileResponse(
        report.pdf_file.open("rb"),
        content_type="application/pdf",
        as_attachment=True,
        filename=report.pdf_file.name.split("/")[-1],
    )


@login_required
def report_download_excel(request, report_id):
    """Telecharge l'Excel."""
    _require_rh(request.user)
    report = get_object_or_404(MonthlyReport, id=report_id, organization=request.user.organization)

    if not report.excel_file:
        messages.error(request, "Excel non disponible")
        return redirect("reports_list")

    return FileResponse(
        report.excel_file.open("rb"),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        filename=report.excel_file.name.split("/")[-1],
    )


@login_required
@require_POST
def report_send(request, report_id):
    """Envoie le rapport par email."""
    _require_rh(request.user)
    report = get_object_or_404(MonthlyReport, id=report_id, organization=request.user.organization)

    sent = send_report_email(report)

    if sent:
        messages.success(request, f"Rapport envoye a {sent} destinataire(s)")
    else:
        messages.warning(request, "Aucun envoi - verifie que le rapport est pret")

    return redirect("reports_list")
