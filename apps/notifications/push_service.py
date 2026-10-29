"""Service Push — avec cleanup automatique."""
import base64
import json
import logging

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


def _normalize_vapid_key(private_key_str):
    """Convertit PEM -> DER base64url."""
    if not private_key_str:
        return ""

    if not private_key_str.strip().startswith("-----"):
        return private_key_str.strip().replace("\\n", "").replace("\\r", "")

    try:
        from cryptography.hazmat.primitives import serialization

        pem_bytes = private_key_str.replace("\\n", "\n").encode("utf-8")
        private_key = serialization.load_pem_private_key(pem_bytes, password=None)

        der_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        return base64.urlsafe_b64encode(der_bytes).decode("ascii").rstrip("=")
    except Exception as e:
        logger.error(f"Erreur conversion cle VAPID : {e}")
        return ""


def _get_vapid_claims():
    email = getattr(settings, "PUSH_CONTACT_EMAIL", "admin@zionpay.app")
    return {"sub": f"mailto:{email}"}


def cleanup_invalid_subscriptions(user=None):
    """Supprime les abonnements invalides ou anciens.

    Garde seulement le plus recent par user.
    """
    from .models import PushSubscription

    qs = PushSubscription.objects.all()
    if user:
        qs = qs.filter(user=user)

    # Grouper par user
    users = qs.values_list("user_id", flat=True).distinct()
    deleted = 0

    for uid in users:
        subs = list(PushSubscription.objects.filter(user_id=uid).order_by("-created_at"))
        # Garder le plus recent actif, supprimer les autres
        kept = False
        for sub in subs:
            if not kept and sub.is_active:
                kept = True
                continue
            sub.delete()
            deleted += 1

    return deleted


def send_push_to_user(user, title, body, url="/", icon="/static/img/icon-192.svg", data=None):
    """Envoie un push. Nettoie les subscriptions invalides automatiquement."""
    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        logger.warning("pywebpush non installe")
        return 0

    from .models import PushSubscription

    # Preparer les cles
    vapid_private_raw = getattr(settings, "VAPID_PRIVATE_KEY", "")
    vapid_public = getattr(settings, "VAPID_PUBLIC_KEY", "")

    if not vapid_private_raw or not vapid_public:
        logger.warning("VAPID keys non configurees")
        return 0

    vapid_private = _normalize_vapid_key(vapid_private_raw)
    if not vapid_private:
        logger.error("Conversion VAPID echouee")
        return 0

    # ─── Nettoyer avant envoi ───
    # Garder uniquement le plus recent abonnement actif
    all_subs = list(PushSubscription.objects.filter(user=user).order_by("-created_at"))

    if not all_subs:
        logger.info(f"Aucune souscription pour {user.email}")
        return 0

    # Ne garder que le plus recent
    latest = all_subs[0]
    for old_sub in all_subs[1:]:
        logger.info(f"Suppression ancien abonnement : {old_sub.endpoint[:50]}")
        old_sub.delete()

    if not latest.is_active:
        latest.is_active = True
        latest.save(update_fields=["is_active"])

    # Construire payload
    payload = {
        "title": title,
        "body": body,
        "icon": icon,
        "badge": "/static/img/icon-192.svg",
        "url": url,
        "data": data or {},
        "timestamp": int(timezone.now().timestamp() * 1000),
    }

    # ─── Envoi ───
    sent = 0
    try:
        webpush(
            subscription_info=latest.to_dict(),
            data=json.dumps(payload),
            vapid_private_key=vapid_private,
            vapid_claims=_get_vapid_claims(),
            timeout=10,
        )
        latest.last_used_at = timezone.now()
        latest.save(update_fields=["last_used_at"])
        sent = 1
        logger.info(f"Push OK pour {user.email}")

    except WebPushException as e:
        status = e.response.status_code if e.response is not None else None
        logger.warning(f"Push failed pour {user.email} (HTTP {status}) : {e}")

        if status in (404, 410):
            # Abonnement mort : le supprimer
            logger.info(f"Suppression abonnement mort : {latest.endpoint[:50]}")
            latest.delete()

    except Exception as e:
        logger.exception(f"Erreur push : {e}")

    return sent


def send_push_to_org_admins(organization, title, body, url="/"):
    """Envoie a tous les admins."""
    from apps.accounts.models import User

    admins = User.objects.filter(
        organization=organization,
        role__in=["ADMIN", "GESTIONNAIRE"],
        is_active=True,
    )

    total = 0
    for admin in admins:
        total += send_push_to_user(admin, title, body, url)
    return total
