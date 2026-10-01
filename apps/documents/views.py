from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import FileResponse
from apps.orders.models import Order
from .models import PurchaseOrderDocument


@login_required
def download_purchase_order_pdf(request, order_id):
    """Télécharge le PDF du bon de commande."""
    order = get_object_or_404(Order, id=order_id, member=request.user)
    doc = get_object_or_404(PurchaseOrderDocument, order=order)
    return FileResponse(doc.file.open('rb'), as_attachment=True, filename=f"BC_{order.order_number}.pdf")
