"""Service de generation du PDF d'une Demande d'Achat."""
import hashlib
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.utils import timezone


def generate_da_pdf(purchase_request):
    """Genere le PDF de la DA avec les signatures et QR codes.

    Retourne un ContentFile pret a etre sauvegarde.
    """
    from .models import DASignature

    # Collecter les signatures valides
    signatures = DASignature.objects.filter(
        purchase_request=purchase_request, is_revoked=False,
    ).order_by("signed_at")

    context = {
        "da": purchase_request,
        "organization": purchase_request.organization,
        "requester": purchase_request.requester,
        "service": purchase_request.service,
        "direction": purchase_request.service.direction if purchase_request.service else None,
        "lines": purchase_request.items.select_related("item", "item__category"),
        "signatures": signatures,
        "generated_at": timezone.now(),
        "history": purchase_request.history.select_related("actor"),
    }

    html = render_to_string("da/pdf/document.html", context)

    try:
        from xhtml2pdf import pisa
        buf = BytesIO()
        result = pisa.CreatePDF(html, dest=buf, encoding="utf-8")
        if result.err:
            raise Exception(f"xhtml2pdf error: {result.err}")
        pdf_bytes = buf.getvalue()
    except ImportError:
        pdf_bytes = html.encode("utf-8")

    filename = f"{purchase_request.number}.pdf"
    return ContentFile(pdf_bytes, name=filename)


def get_da_document_hash(purchase_request):
    """Hash SHA-256 du PDF genere (pour preuve)."""
    pdf = generate_da_pdf(purchase_request)
    return hashlib.sha256(pdf.read()).hexdigest()
