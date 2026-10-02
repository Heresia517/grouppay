"""RG-15 : double confirmation — le service paie confirme via webhook."""
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json


@csrf_exempt
def deduction_webhook(request):
    """
    POST /api/v1/deductions/webhook/
    Body: {"reference": "DED-SONABEL-2026-000001", "status": "CONFIRMEE", "payroll_ref": "PAIE-2026-10-XXX"}
    """
    if request.method != "POST":
        return JsonResponse({"error": "METHOD_NOT_ALLOWED"}, status=405)

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({"error": "INVALID_JSON"}, status=400)

    ref = data.get("reference")
    status = data.get("status")

    from .models import DeductionTransmission
    try:
        ded = DeductionTransmission.objects.get(reference=ref)
    except DeductionTransmission.DoesNotExist:
        return JsonResponse({"error": "NOT_FOUND"}, status=404)

    if status == "CONFIRMEE":
        ded.status = "CONFIRMEE"
        ded.confirmed_at = timezone.now()
        ded.confirmation_reference = data.get("payroll_ref", "")
    elif status == "ECHEC":
        ded.status = "ECHEC"
        ded.error_message = data.get("reason", "")
    else:
        return JsonResponse({"error": "INVALID_STATUS"}, status=400)

    ded.save(update_fields=["status", "confirmed_at", "confirmation_reference", "error_message"])
    return JsonResponse({"ok": True, "reference": ref, "status": ded.status})


def confirm_deduction(reference, payroll_ref=""):
    """Version programmatique (utilisée en tests)."""
    from .models import DeductionTransmission
    ded = DeductionTransmission.objects.get(reference=reference)
    ded.status = "CONFIRMEE"
    ded.confirmed_at = timezone.now()
    ded.confirmation_reference = payroll_ref
    ded.save()
    return ded
