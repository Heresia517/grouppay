"""Vues du module core — health check et monitoring."""
from django.conf import settings
from django.http import JsonResponse


def health(request):
    """
    Endpoint de santé pour monitoring (uptime).
    
    Retourne un JSON avec l'état du système.
    Utilisé par les load balancers, Kubernetes, UptimeRobot, etc.
    """
    return JsonResponse({
        "status": "ok",
        "service": "zionpay",
        "env": getattr(settings, "SENTRY_ENVIRONMENT", "development"),
        "debug": settings.DEBUG,
        "sentry_enabled": bool(getattr(settings, "SENTRY_DSN", "")),
    })


def sentry_test(request):
    """
    Test Sentry (dev only).
    Envoie un event de test pour vérifier l'intégration.
    """
    if not settings.DEBUG:
        return JsonResponse({"error": "Not available in production"}, status=403)

    try:
        import sentry_sdk
        sentry_sdk.capture_message("Test ZionPay Sentry", level="info")
        return JsonResponse({
            "ok": True,
            "message": "Event sent to Sentry (check your dashboard)",
        })
    except ImportError:
        return JsonResponse({
            "ok": False,
            "error": "sentry-sdk non installé : pip install sentry-sdk",
        }, status=500)
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)
