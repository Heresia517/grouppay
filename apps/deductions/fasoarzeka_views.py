"""Vues Faso Arzeka : initier paiement + webhook statut."""
import json
import logging
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.decorators import login_required
from django.conf import settings

from .fasoarzeka_service import get_client, FASOARZEKA_AVAILABLE

logger = logging.getLogger(__name__)


@login_required
def fasoarzeka_payer(request, order_id):
    """Initie un paiement Faso Arzeka pour une commande."""
    from apps.orders.models import Order
    order = Order.objects.filter(id=order_id, member=request.user).first()
    if not order:
        return JsonResponse({"error": "Commande introuvable"}, status=404)

    client = get_client()
    try:
        result = client.initier_paiement(
            montant=int(order.total_amount),
            reference=f"GP-{order.id}",
            prenom=request.user.first_name,
            nom=request.user.last_name,
            telephone=getattr(request.user, "phone", "") or "",
            description=f"Commande GroupPay #{order.id}",
        )
        return JsonResponse(result)
    except Exception as e:
        logger.exception("Faso Arzeka initiate error")
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


@csrf_exempt
@require_POST
def fasoarzeka_webhook(request):
    """Webhook : Faso Arzeka notifie le statut d'un paiement."""
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        payload = request.POST.dict()

    logger.info(f"[FasoArzeka webhook] {payload}")
    reference = payload.get("mapped_order_id") or payload.get("mappedOrderId") or ""
    statut = (payload.get("status") or "").upper()

    if statut in ("SUCCESS", "PAID", "COMPLETED") and reference.startswith("GP-"):
        try:
            from apps.orders.models import Order
            oid = reference.replace("GP-", "")
            order = Order.objects.filter(id=oid).first()
            if order:
                logger.info(f"[FasoArzeka] Commande {order.id} payée")
        except Exception:
            logger.exception("Erreur traitement webhook")

    return HttpResponse("OK", status=200)


@require_GET
def fasoarzeka_status(request):
    """Endpoint de diagnostic."""
    return JsonResponse({
        "package_installed": FASOARZEKA_AVAILABLE,
        "enabled": settings.FASOARZEKA["ENABLED"],
        "plateforme": "Faso Arzeka (Burkina Faso)",
        "site": "https://my.fasoarzeka.bf",
        "ussd": "*700#",
    })
