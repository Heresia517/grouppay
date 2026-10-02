from celery import shared_task


@shared_task(name="catalog.check_low_stock_alerts")
def check_low_stock_alerts():
    """RG-21 : notifie les gestionnaires des produits sous seuil."""
    from apps.organizations.models import Organization
    from .services import check_low_stock
    from apps.notifications.models import Notification

    total = 0
    for org in Organization.objects.filter(status__in=["TRIAL", "ACTIVE"]):
        low = check_low_stock(org)
        if low:
            for user in org.users.filter(role__in=["ADMIN", "GESTIONNAIRE"]):
                Notification.objects.create(
                    organization=org,
                    recipient=user,
                    channel="IN_APP",
                    title=f"{len(low)} produit(s) en stock critique",
                    body=", ".join(p["name"] for p in low[:5]),
                )
                total += 1
    return {"notifications_sent": total}
