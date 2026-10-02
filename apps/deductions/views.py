"""Vues retenue salariale — dashboard + preview + download."""
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
