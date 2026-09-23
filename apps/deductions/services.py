import csv
import io
from django.core.files.base import ContentFile
from django.db import transaction
from .models import DeductionExportBatch, DeductionTransmission


@transaction.atomic
def generate_export_batch(organization, period_start, period_end, generated_by):
    """US-05 : génère le fichier CSV et fait passer les transmissions
    EN_ATTENTE de la période à ENVOYEE."""
    transmissions = DeductionTransmission.objects.filter(
        organization=organization,
        status="EN_ATTENTE",
        order__created_at__date__gte=period_start,
        order__created_at__date__lte=period_end,
    ).select_related("order", "order__member")

    if not transmissions.exists():
        return None

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["matricule", "nom", "email", "reference_commande", "montant", "devise"])

    for t in transmissions:
        member = t.order.member
        writer.writerow([
            member.internal_id or "N/A",
            member.email,
            member.email,
            t.reference,
            t.order.total_amount,
            t.order.currency_code,
        ])

    batch = DeductionExportBatch.objects.create(
        organization=organization,
        period_start=period_start,
        period_end=period_end,
        row_count=transmissions.count(),
        generated_by=generated_by,
    )
    batch.file.save(f"export_{batch.id}.csv", ContentFile(buffer.getvalue().encode("utf-8")))

    transmissions.update(status="ENVOYEE", export_batch=batch)

    return batch
