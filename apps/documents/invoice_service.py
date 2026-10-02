"""Service de génération de factures PDF."""
import hashlib
from datetime import date
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.utils import timezone

from apps.orders.models import Order
from .models import InvoiceDocument


def generate_invoice_number(order):
    """FAC-SONABEL-2026-000001"""
    year = order.created_at.year if order.created_at else date.today().year
    prefix = f"FAC-{order.organization.slug.upper()}-{year}-"
    count = InvoiceDocument.objects.filter(
        invoice_number__startswith=prefix
    ).count()
    return f"{prefix}{count + 1:06d}"


def generate_invoice_pdf(order):
    """Génère et stocke la facture PDF de la commande."""
    doc = InvoiceDocument.objects.filter(order=order).first()
    if doc and doc.file:
        return doc

    if not doc:
        doc = InvoiceDocument.objects.create(
            order=order,
            invoice_number=generate_invoice_number(order),
        )

    html = render_to_string("documents/invoice_pdf.html", {
        "order": order,
        "organization": order.organization,
        "member": order.member,
        "items": order.items.select_related("product").all(),
        "generated_at": timezone.now(),
        "invoice_number": doc.invoice_number,
    })

    try:
        from xhtml2pdf import pisa
        buf = BytesIO()
        result = pisa.CreatePDF(html, dest=buf, encoding="utf-8")
        if result.err:
            raise Exception(f"xhtml2pdf error: {result.err}")
        pdf_bytes = buf.getvalue()
    except ImportError:
        # Fallback : écrire le HTML comme fichier (utile si xhtml2pdf absent)
        pdf_bytes = html.encode("utf-8")

    # Save
    filename = f"{doc.invoice_number}.pdf"
    doc.file.save(filename, ContentFile(pdf_bytes), save=False)
    doc.file_hash = hashlib.sha256(pdf_bytes).hexdigest()
    doc.save(update_fields=["file", "file_hash"])
    return doc


def get_or_create_invoice(order):
    """Helper idempotent."""
    doc = InvoiceDocument.objects.filter(order=order).first()
    if doc and doc.file:
        return doc
    return generate_invoice_pdf(order)
