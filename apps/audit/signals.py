"""Signaux d'audit automatiques sur Order et User."""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver


@receiver(post_save, sender="orders.Order")
def audit_order(sender, instance, created, **kwargs):
    from .models import AuditLog
    AuditLog.objects.create(
        organization=instance.organization,
        user=instance.member,
        action="order_created" if created else "order_updated",
        resource_type="Order",
        resource_id=str(instance.id),
        new_values={"status": instance.status, "total": str(instance.total_amount)},
        metadata={"order_number": instance.order_number},
    )
