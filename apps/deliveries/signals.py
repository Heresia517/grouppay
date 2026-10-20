"""Signaux automatiques pour le module Livraisons."""
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.orders.models import Order
from .models import Delivery


@receiver(post_save, sender=Order, dispatch_uid="auto_create_delivery_on_validation")
def create_delivery_on_validation(sender, instance, created, **kwargs):
    """
    Cree automatiquement une fiche de livraison quand une commande passe a VALIDEE.
    (RG-16 : Livraison auto)
    """
    if instance.status != "VALIDEE":
        return

    # Ne pas creer si une livraison existe deja
    if Delivery.objects.filter(order=instance).exists():
        return

    # Assigner un livreur disponible (le premier de l'org)
    livreur = User.objects.filter(
        organization=instance.organization,
        role="LIVREUR"
    ).order_by("?").first()

    try:
        Delivery.objects.create(
            order=instance,
            courier=livreur,
            status="ASSIGNEE",
        )
        print(f"[SIGNAL] Livraison creee pour {instance.order_number} (livreur: {livreur.email if livreur else 'non assigne'})")
    except Exception as e:
        print(f"[SIGNAL] Erreur creation livraison : {e}")
