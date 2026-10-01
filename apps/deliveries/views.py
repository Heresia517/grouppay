from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from .models import Delivery, DeliveryNoteDocument
from apps.orders.models import OrderStatusHistory


@login_required
def courier_deliveries(request):
    """Liste des livraisons affectées au livreur."""
    if request.user.role != "LIVREUR":
        return redirect('/')
    
    deliveries = Delivery.objects.filter(courier=request.user).order_by("-created_at")
    return render(request, "deliveries/courier_deliveries.html", {"deliveries": deliveries})


@login_required
def delivery_detail(request, delivery_id):
    """Détail d'une livraison."""
    delivery = get_object_or_404(Delivery, id=delivery_id, courier=request.user)
    return render(request, "deliveries/delivery_detail.html", {"delivery": delivery})


@login_required
@require_http_methods(["POST"])
def update_delivery_status(request, delivery_id):
    """Change le statut de la livraison."""
    delivery = get_object_or_404(Delivery, id=delivery_id, courier=request.user)
    new_status = request.POST.get("status")

    if new_status in ["EN_COURS", "LIVREE", "ECHEC"]:
        delivery.status = new_status
        if new_status == "LIVREE":
            delivery.delivered_at = timezone.now()
            delivery.order.status = "LIVREE"
            delivery.order.save()
            OrderStatusHistory.objects.create(
                order=delivery.order,
                from_status="EN_LIVRAISON",
                to_status="LIVREE",
                actor=request.user
            )
        delivery.save()

    return redirect("delivery_detail", delivery_id=delivery_id)
