"""Vues push."""
import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import PushSubscription
from .push_service import send_push_to_user

logger = logging.getLogger(__name__)


def vapid_public_key(request):
    """Retourne la cle publique VAPID."""
    from django.conf import settings
    return JsonResponse({
        "publicKey": getattr(settings, "VAPID_PUBLIC_KEY", ""),
    })


@login_required
@require_POST
def subscribe(request):
    """Enregistre une souscription.

    IMPORTANT : supprime TOUTES les anciennes souscriptions
    pour eviter les abonnements morts.
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON invalide"}, status=400)

    endpoint = data.get("endpoint")
    keys = data.get("keys", {})
    p256dh = keys.get("p256dh")
    auth = keys.get("auth")

    if not endpoint or not p256dh or not auth:
        return JsonResponse({"error": "Donnees incompletes"}, status=400)

    # ─── Nettoyer TOUTES les anciennes souscriptions du user ───
    deleted_count = PushSubscription.objects.filter(user=request.user).delete()[0]

    if deleted_count:
        logger.info(f"Nettoyage {deleted_count} ancienne(s) souscription(s) pour {request.user.email}")

    # ─── Creer la nouvelle ───
    sub = PushSubscription.objects.create(
        user=request.user,
        endpoint=endpoint,
        p256dh=p256dh,
        auth=auth,
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:255],
        is_active=True,
    )

    logger.info(f"Nouvelle souscription pour {request.user.email}")

    return JsonResponse({
        "ok": True,
        "id": str(sub.id),
        "replaced": deleted_count,
    })


@login_required
@require_POST
def unsubscribe(request):
    """Desactive une souscription."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON invalide"}, status=400)

    endpoint = data.get("endpoint")
    if not endpoint:
        return JsonResponse({"error": "endpoint requis"}, status=400)

    deleted = PushSubscription.objects.filter(
        user=request.user, endpoint=endpoint,
    ).delete()[0]

    return JsonResponse({"ok": True, "deleted": deleted})


@login_required
@require_POST
def test_push(request):
    """Envoie une notification de test."""
    # Nettoyer d'abord
    from .push_service import cleanup_invalid_subscriptions
    cleanup_invalid_subscriptions(user=request.user)

    sent = send_push_to_user(
        request.user,
        title="GroupPay",
        body="Les notifications push fonctionnent !",
        url="/",
    )

    return JsonResponse({"ok": True, "sent": sent})


@login_required
def push_test_page(request):
    from django.shortcuts import render
    return render(request, "accounts/push_test.html")


@login_required
def push_test_v5_page(request):
    from django.shortcuts import render
    return render(request, "accounts/push_test_v5.html")


@login_required
def subscription_info(request):
    """Debug : affiche les abonnements du user."""
    subs = PushSubscription.objects.filter(user=request.user)
    return JsonResponse({
        "count": subs.count(),
        "subscriptions": [
            {
                "id": str(s.id),
                "endpoint": s.endpoint[:80] + "...",
                "is_active": s.is_active,
                "created_at": s.created_at.isoformat(),
                "last_used": s.last_used_at.isoformat() if s.last_used_at else None,
            }
            for s in subs
        ],
    })
