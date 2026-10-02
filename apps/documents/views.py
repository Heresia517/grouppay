from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required

from .models import PurchaseOrderDocument
from .services import generate_purchase_order_pdf
from apps.orders.models import Order


def _get_or_create_pdf(order):
    """Récupère ou génère le PDF à la volée."""
    doc = PurchaseOrderDocument.objects.filter(order=order).first()
    if not doc or not doc.file:
        doc = generate_purchase_order_pdf(order)
    return doc


def _check_permission(request, order):
    is_owner = order.member_id == request.user.id
    is_rh = request.user.role in ("ADMIN", "GESTIONNAIRE")
    same_org = order.organization_id == request.user.organization_id
    return is_owner or (is_rh and same_org)


@login_required
def preview_order_html(request, order_id):
    """Aperçu HTML stylé du bon de commande."""
    order = get_object_or_404(Order, id=order_id)
    if not _check_permission(request, order):
        raise Http404("Commande introuvable")
    items = order.items.select_related("product").all()
    return render(request, "documents/preview.html", {"order": order, "items": items})


@login_required
def preview_purchase_order_pdf(request, order_id):
    """Affiche le PDF dans le navigateur (inline)."""
    order = get_object_or_404(Order, id=order_id)
    if not _check_permission(request, order):
        raise Http404("Commande introuvable")
    doc = _get_or_create_pdf(order)
    return FileResponse(doc.file.open("rb"), content_type="application/pdf", as_attachment=False)


@login_required
def download_purchase_order_pdf(request, order_id):
    """Force le téléchargement du PDF."""
    order = get_object_or_404(Order, id=order_id)
    if not _check_permission(request, order):
        raise Http404("Commande introuvable")
    doc = _get_or_create_pdf(order)
    return FileResponse(
        doc.file.open("rb"),
        as_attachment=True,
        filename=f"BC-{order.order_number}.pdf",
    )



# ═══════════════════════════════════════════════════════════════
# FACTURES
# ═══════════════════════════════════════════════════════════════
@login_required
def preview_invoice_html(request, order_id):
    """Aperçu HTML stylé de la facture."""
    order = get_object_or_404(Order, id=order_id)
    if not _check_permission(request, order):
        raise Http404("Commande introuvable")

    from .invoice_service import get_or_create_invoice
    doc = get_or_create_invoice(order)

    return render(request, "documents/invoice.html", {
        "order": order,
        "items": order.items.select_related("product").all(),
        "invoice": doc,
    })


@login_required
def preview_invoice_pdf(request, order_id):
    """Affiche le PDF facture inline."""
    order = get_object_or_404(Order, id=order_id)
    if not _check_permission(request, order):
        raise Http404

    from .invoice_service import get_or_create_invoice
    doc = get_or_create_invoice(order)

    return FileResponse(doc.file.open("rb"), content_type="application/pdf", as_attachment=False)


@login_required
def download_invoice_pdf(request, order_id):
    """Force le téléchargement de la facture."""
    order = get_object_or_404(Order, id=order_id)
    if not _check_permission(request, order):
        raise Http404

    from .invoice_service import get_or_create_invoice
    from django.utils import timezone
    doc = get_or_create_invoice(order)

    # Tracker le download
    doc.downloaded_at = timezone.now()
    doc.download_count = (doc.download_count or 0) + 1
    doc.save(update_fields=["downloaded_at", "download_count"])

    return FileResponse(
        doc.file.open("rb"),
        as_attachment=True,
        filename=f"{doc.invoice_number}.pdf",
    )
