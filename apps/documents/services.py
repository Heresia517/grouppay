from io import BytesIO
from django.template.loader import render_to_string
from django.core.files.base import ContentFile
from xhtml2pdf import pisa
from .models import PurchaseOrderDocument


def generate_purchase_order_pdf(order):
    html_content = render_to_string("documents/purchase_order.html", {
        "order": order,
        "organization": order.organization,
    })

    buffer = BytesIO()
    result = pisa.CreatePDF(html_content, dest=buffer)
    if result.err:
        raise ValueError("Erreur de génération du PDF")

    doc, _ = PurchaseOrderDocument.objects.update_or_create(
        order=order,
        defaults={},
    )
    doc.file.save(f"BC_{order.order_number}.pdf", ContentFile(buffer.getvalue()), save=True)
    return doc
