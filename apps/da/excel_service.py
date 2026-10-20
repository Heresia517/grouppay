"""Service d'export Excel pour les DA."""
from datetime import timedelta
from io import BytesIO

from django.utils import timezone

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    OPENPYXL_OK = True
except ImportError:
    OPENPYXL_OK = False

from .models import PurchaseRequest, PurchaseRequestItem, DAStockMovement


def _style_header(cell):
    cell.font = Font(bold=True, color="FFFFFF", size=11)
    cell.fill = PatternFill("solid", fgColor="2563EB")
    cell.alignment = Alignment(horizontal="center", vertical="center")


def _style_title(cell):
    cell.font = Font(bold=True, size=14, color="1E3A8A")


def _auto_width(ws):
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            if cell.value:
                max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = min(max_len + 4, 50)


def export_da_list_excel(purchase_requests, title="Demandes d'Achat"):
    """Export la liste des DA au format Excel avec 3 feuilles.

    Args:
        purchase_requests: queryset ou list de PurchaseRequest
        title: titre general du document

    Returns:
        BytesIO contenant le fichier xlsx
    """
    if not OPENPYXL_OK:
        raise ImportError("openpyxl non installe. Lancez : pip install openpyxl")

    wb = Workbook()

    # ═══ Feuille 1 : Synthese ═══
    ws1 = wb.active
    ws1.title = "Synthese"
    ws1["A1"] = title
    ws1["A1"].font = Font(bold=True, size=16, color="1E3A8A")
    ws1["A2"] = f"Genere le {timezone.now().strftime('%d/%m/%Y a %H:%M')}"
    ws1["A2"].font = Font(italic=True, color="64748B", size=10)

    # Stats
    from django.db.models import Sum, Count, Avg
    qs = purchase_requests
    if hasattr(qs, "aggregate"):
        stats = qs.aggregate(
            total_count=Count("id"),
            total_amount=Sum("total_amount"),
            avg_amount=Avg("total_amount"),
        )
        total_count = stats["total_count"] or 0
        total_amount = stats["total_amount"] or 0
        avg_amount = stats["avg_amount"] or 0
    else:
        total_count = len(qs)
        total_amount = sum(r.total_amount for r in qs)
        avg_amount = total_amount / total_count if total_count else 0

    ws1.append([])
    ws1.append(["Indicateur", "Valeur"])
    for cell in ws1[4]:
        _style_header(cell)

    currency = "FCFA"
    if total_count and hasattr(qs, "first"):
        first = qs.first() if hasattr(qs, "first") else (qs[0] if qs else None)
        if first:
            currency = first.currency_code

    kpis = [
        ("Nombre total de DA", total_count),
        ("Montant total", float(total_amount)),
        ("Montant moyen", float(avg_amount)),
        ("Devise", currency),
    ]
    for label, val in kpis:
        ws1.append([label, val])

    # Repartition par statut
    ws1.append([])
    ws1.append(["Repartition par statut"])
    ws1[ws1.max_row][0].font = Font(bold=True, size=12)

    ws1.append(["Statut", "Nombre", "Montant"])
    for cell in ws1[ws1.max_row]:
        _style_header(cell)

    if hasattr(qs, "values"):
        by_status = (
            qs.values("status")
            .annotate(count=Count("id"), amount=Sum("total_amount"))
            .order_by("-count")
        )
        status_labels = dict(PurchaseRequest.STATUS_CHOICES)
        for s in by_status:
            ws1.append([
                status_labels.get(s["status"], s["status"]),
                s["count"],
                float(s["amount"] or 0),
            ])

    _auto_width(ws1)

    # ═══ Feuille 2 : Detail des DA ═══
    ws2 = wb.create_sheet("DA (detail)")
    headers = [
        "N° DA", "Date", "Demandeur", "Service", "Direction",
        "Statut", "Priorite", "Montant", "Devise",
        "Motif", "Fournisseur", "Validee par", "Date validation",
    ]
    ws2.append(headers)
    for cell in ws2[1]:
        _style_header(cell)

    for da in purchase_requests:
        ws2.append([
            da.number,
            da.created_at.strftime("%d/%m/%Y") if da.created_at else "",
            da.requester.email,
            da.service.name if da.service else "",
            da.service.direction.name if da.service and da.service.direction else "",
            da.get_status_display(),
            da.get_priority_display(),
            float(da.total_amount),
            da.currency_code,
            (da.purpose or "")[:100],
            da.supplier_name or "",
            da.validated_by.email if da.validated_by else "",
            da.validated_at.strftime("%d/%m/%Y") if da.validated_at else "",
        ])

    _auto_width(ws2)

    # ═══ Feuille 3 : Lignes d'articles ═══
    ws3 = wb.create_sheet("Articles commandes")
    ws3.append([
        "N° DA", "Article", "Categorie", "Reference",
        "Quantite", "Unite", "Prix unitaire", "Sous-total",
    ])
    for cell in ws3[1]:
        _style_header(cell)

    # Recuperer les IDs
    da_ids = [da.id for da in purchase_requests] if not hasattr(purchase_requests, "values_list") else list(purchase_requests.values_list("id", flat=True))

    items = PurchaseRequestItem.objects.filter(request_id__in=da_ids).select_related(
        "request", "item", "item__category",
    )
    for line in items:
        ws3.append([
            line.request.number,
            line.item.name,
            line.item.category.name,
            line.item.reference or "",
            line.quantity,
            line.item.get_unit_display(),
            float(line.unit_price),
            float(line.subtotal),
        ])

    _auto_width(ws3)

    # ═══ Feuille 4 : Historique (si peu de DA) ═══
    if total_count <= 100:
        ws4 = wb.create_sheet("Historique")
        ws4.append(["N° DA", "Date", "Statut precedent", "Nouveau statut", "Acteur", "Commentaire"])
        for cell in ws4[1]:
            _style_header(cell)

        for da in purchase_requests:
            for h in da.history.order_by("created_at"):
                ws4.append([
                    da.number,
                    h.created_at.strftime("%d/%m/%Y %H:%M"),
                    h.from_status or "—",
                    h.to_status,
                    h.actor.email if h.actor else "Systeme",
                    (h.comment or "")[:100],
                ])
        _auto_width(ws4)

    # Output
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


def export_single_da_excel(purchase_request):
    """Export d'une seule DA avec toutes ses donnees."""
    return export_da_list_excel([purchase_request], title=f"DA {purchase_request.number}")
