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


"""Taches Celery pour les relances paniers."""
from celery import shared_task


@shared_task(name="orders.send_abandoned_cart_reminders")
def send_abandoned_cart_reminders():
    """Envoie les relances quotidiennes aux paniers abandonnes."""
    from .cart_recovery import get_abandoned_carts, send_cart_recovery

    carts = get_abandoned_carts(hours_min=24, hours_max=72)
    sent = 0
    for cart in carts[:200]:
        success, _ = send_cart_recovery(cart, channel="EMAIL")
        if success:
            sent += 1

    return {"sent": sent, "total": carts.count()}



@shared_task(name="orders.generate_monthly_reports")
def generate_monthly_reports():
    """Genere automatiquement les rapports du mois precedent (le 1er du mois)."""
    from .report_service import generate_report, send_report_email
    from .models import MonthlyReport

    results = generate_report()

    # Envoyer les rapports par email
    reports = MonthlyReport.objects.filter(
        status="READY",
        sent_at__isnull=True,
    )
    for report in reports:
        send_report_email(report)

    return {"generated": len(results), "sent": reports.count()}
