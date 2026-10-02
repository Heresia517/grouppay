from celery import shared_task
from datetime import timedelta
from django.utils import timezone


@shared_task(name="orders.cleanup_expired_carts")
def cleanup_expired_carts(days=30):
    """RG-09 : supprime les paniers inactifs depuis N jours."""
    from .models import Cart
    cutoff = timezone.now() - timedelta(days=days)
    qs = Cart.objects.filter(status="OPEN", created_at__lt=cutoff)
    n = qs.count()
    qs.update(status="EXPIRED")
    return {"expired_carts": n}
