from celery import shared_task
from django.utils import timezone


@shared_task(name="deductions.cleanup_expired_transmissions")
def cleanup_expired_transmissions():
    """RG-11 : marque EXPIREE les transmissions > 30 jours non confirmées."""
    from .models import DeductionTransmission
    qs = DeductionTransmission.objects.filter(
        status__in=["EN_ATTENTE", "ENVOYEE"],
        expires_at__lt=timezone.now(),
    )
    n = qs.update(status="EXPIREE")
    return {"expired": n}
