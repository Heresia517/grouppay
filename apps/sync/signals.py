from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.conf import settings
from .models import SyncOperation, SyncState

# Modèles synchronisés (adapter selon vos besoins)
SYNCED_MODELS = [
    "orders.Order", "orders.OrderItem",
    "catalog.Product", "catalog.Review",
    "accounts.User",
]


def _client_id():
    import socket
    cid = socket.gethostname()
    SyncState.objects.get_or_create(client_id=cid)
    return cid


def _serialize(instance):
    """Sérialise une instance en JSON-compatible (UUID/Decimal/datetime/FK)."""
    import uuid as _uuid
    from decimal import Decimal

    def _val(v):
        if v is None:
            return None
        if isinstance(v, _uuid.UUID):
            return str(v)
        if isinstance(v, Decimal):
            return float(v)
        if isinstance(v, (int, float, str, bool)):
            return v
        if hasattr(v, "isoformat"):        # datetime, date, time
            return v.isoformat()
        if hasattr(v, "pk"):               # instance de modèle
            return str(v.pk)
        return str(v)

    return {field.name: _val(getattr(instance, field.name)) for field in instance._meta.fields}


@receiver(post_save, dispatch_uid="sync_capture_save")
def capture_save(sender, instance, created, **kwargs):
    if not getattr(settings, "IS_DESKTOP", False):
        return
    name = f"{sender._meta.app_label}.{sender.__name__}"
    if name not in SYNCED_MODELS:
        return
    SyncOperation.objects.create(
        client_id=_client_id(),
        model_name=name,
        object_id=str(instance.pk),
        operation="create" if created else "update",
        payload=_serialize(instance),
    )


@receiver(post_delete, dispatch_uid="sync_capture_delete")
def capture_delete(sender, instance, **kwargs):
    if not getattr(settings, "IS_DESKTOP", False):
        return
    name = f"{sender._meta.app_label}.{sender.__name__}"
    if name not in SYNCED_MODELS:
        return
    SyncOperation.objects.create(
        client_id=_client_id(),
        model_name=name,
        object_id=str(instance.pk),
        operation="delete",
        payload={},
    )
