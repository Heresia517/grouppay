"""Export Excel du dashboard RH."""
from datetime import timedelta
from io import BytesIO

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Sum, Count, Avg
from django.http import HttpResponse
from django.utils import timezone

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    OPENPYXL_OK = True
except ImportError:
    OPENPYXL_OK = False

from .models import Order, OrderItem


def _require_rh(user):
    if user.role not in ("ADMIN", "GESTIONNAIRE"):
        raise PermissionDenied("Accès réservé RH/Admin")


@login_required
def export_dashboard_excel(request):
    """Génère un fichier Excel avec 3 feuilles : KPIs, Commandes, Top produits."""
    if not OPENPYXL_OK:
        return HttpResponse("openpyxl non installé. Lancez: pip install openpyxl", status=500)

    _require_rh(request.user)
    org = request.user.organization
    now = timezone.now()

    period = request.GET.get("period", "30")
    try:
        days = int(period)
    except ValueError:
        days = 30
    start = now - timedelta(days=days)

    qs = Order.objects.filter(organization=org, created_at__gte=start)
    qs_valid = qs.filter(status__in=["VALIDEE", "EN_LIVRAISON", "LIVREE"])

    wb = Workbook()

    # ─── Styles
    title_font = Font(bold=True, size=14, color="1E3A8A")
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="2563EB")
    money_fmt = '#,##0 "XOF"'
    border = Border(
        left=Side(style="thin", color="E2E8F0"),
        right=Side(style="thin", color="E2E8F0"),
        top=Side(style="thin", color="E2E8F0"),
        bottom=Side(style="thin", color="E2E8F0"),
    )

    # ═══ Feuille 1 : KPIs
    ws1 = wb.active
    ws1.title = "KPIs"
    ws1["A1"] = f"Dashboard RH — {org.name}"
    ws1["A1"].font = title_font
    ws1["A2"] = f"Période : {start.strftime('%d/%m/%Y')} → {now.strftime('%d/%m/%Y')}"
    ws1["A2"].font = Font(italic=True, color="64748B")

    kpis = [
        ("Chiffre d'affaires", qs_valid.aggregate(s=Sum("total_amount"))["s"] or 0, "XOF"),
        ("Nombre de commandes", qs_valid.count(), ""),
        ("Panier moyen", qs_valid.aggregate(a=Avg("total_amount"))["a"] or 0, "XOF"),
        ("En attente de validation", qs.filter(status="EN_ATTENTE_VALIDATION").count(), ""),
    ]
    ws1.append([])
    ws1.append(["Indicateur", "Valeur", "Devise"])
    for cell in ws1[4]:
        cell.font = header_font
        cell.fill = header_fill
    for label, val, cur in kpis:
        ws1.append([label, float(val), cur])

    # ═══ Feuille 2 : Commandes détaillées
    ws2 = wb.create_sheet("Commandes")
    ws2.append(["N° commande", "Date", "Membre", "Matricule", "Statut", "Montant", "Devise"])
    for cell in ws2[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")

    for o in qs.select_related("member").order_by("-created_at"):
        ws2.append([
            o.order_number,
            o.created_at.strftime("%d/%m/%Y %H:%M"),
            o.member.email,
            o.member.internal_id or "—",
            o.get_status_display(),
            float(o.total_amount),
            o.currency_code,
        ])

    # Largeurs auto
    for col, w in zip("ABCDEFG", [18, 18, 30, 15, 18, 15, 8]):
        ws2.column_dimensions[col].width = w

    # ═══ Feuille 3 : Top produits
    ws3 = wb.create_sheet("Top produits")
    ws3.append(["Produit", "Quantité vendue", "CA généré"])
    for cell in ws3[1]:
        cell.font = header_font
        cell.fill = header_fill

    top = (
        OrderItem.objects.filter(
            order__organization=org,
            order__status__in=["VALIDEE", "EN_LIVRAISON", "LIVREE"],
            order__created_at__gte=start,
        )
        .values("product__name")
        .annotate(qty=Sum("quantity"), ca=Sum("unit_price"))
        .order_by("-qty")[:20]
    )
    for p in top:
        ws3.append([p["product__name"], p["qty"] or 0, float(p["ca"] or 0)])

    for col, w in zip("ABC", [40, 18, 18]):
        ws3.column_dimensions[col].width = w

    # ─── Output
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)

    filename = f"dashboard-{org.slug}-{now.strftime('%Y%m%d')}.xlsx"
    response = HttpResponse(
        buf.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


"""Export PDF du dashboard via xhtml2pdf."""
from datetime import timedelta
from io import BytesIO

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Sum, Count, Avg
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone

from .models import Order, OrderItem
from apps.catalog.services import check_low_stock


def _require_rh(user):
    if user.role not in ("ADMIN", "GESTIONNAIRE"):
        raise PermissionDenied("Acces reserve RH/Admin")


def _pct_delta(cur, prev):
    if not prev:
        return None
    try:
        return round(((float(cur) - float(prev)) / float(prev)) * 100, 1)
    except (ZeroDivisionError, TypeError):
        return None


@login_required
def export_dashboard_pdf(request):
    """Genere le PDF du dashboard avec KPIs, commandes et top produits."""
    _require_rh(request.user)

    try:
        from xhtml2pdf import pisa
    except ImportError:
        return HttpResponse(
            "xhtml2pdf non installe. Lancez: pip install xhtml2pdf",
            status=500,
        )

    org = request.user.organization
    now = timezone.now()

    period = request.GET.get("period", "30")
    try:
        days = int(period)
    except ValueError:
        days = 30
    start = now - timedelta(days=days)
    start_prev = start - timedelta(days=days)

    qs = Order.objects.filter(organization=org)
    qs_valid = qs.filter(status__in=["VALIDEE", "EN_LIVRAISON", "LIVREE"])

    cur = qs_valid.filter(created_at__gte=start)
    prev = qs_valid.filter(created_at__gte=start_prev, created_at__lt=start)

    rev_cur = cur.aggregate(s=Sum("total_amount"))["s"] or 0
    rev_prev = prev.aggregate(s=Sum("total_amount"))["s"] or 0
    avg_cur = cur.aggregate(a=Avg("total_amount"))["a"] or 0
    avg_prev = prev.aggregate(a=Avg("total_amount"))["a"] or 0

    kpis = {
        "revenue": {"value": rev_cur, "delta": _pct_delta(rev_cur, rev_prev)},
        "orders": {"value": cur.count(), "delta": _pct_delta(cur.count(), prev.count())},
        "avg_basket": {"value": avg_cur, "delta": _pct_delta(avg_cur, avg_prev)},
        "pending": qs.filter(status="EN_ATTENTE_VALIDATION").count(),
    }

    orders = list(
        qs.filter(created_at__gte=start)
        .select_related("member")
        .order_by("-created_at")[:200]
    )

    top = list(
        OrderItem.objects.filter(
            order__organization=org,
            order__status__in=["VALIDEE", "EN_LIVRAISON", "LIVREE"],
            order__created_at__gte=start,
        )
        .values("product__name")
        .annotate(qty=Sum("quantity"))
        .order_by("-qty")[:5]
    )
    top_products = [{"name": p["product__name"], "qty": p["qty"] or 0} for p in top]

    html = render_to_string("admin/dashboard_pdf.html", {
        "organization": org,
        "kpis": kpis,
        "orders": orders,
        "top_products": top_products,
        "low_stock": check_low_stock(org),
        "period": days,
        "period_start": start.strftime("%d/%m/%Y"),
        "period_end": now.strftime("%d/%m/%Y"),
        "generated_at": now.strftime("%d/%m/%Y %H:%M"),
    })

    buf = BytesIO()
    pisa.CreatePDF(html, dest=buf, encoding="utf-8")
    buf.seek(0)

    resp = HttpResponse(buf.read(), content_type="application/pdf")
    resp["Content-Disposition"] = (
        f'attachment; filename="dashboard-{org.slug}-{now.strftime("%Y%m%d")}.pdf"'
    )
    return resp


"""Export PDF du dashboard via xhtml2pdf."""
from datetime import timedelta
from io import BytesIO

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Sum, Count, Avg
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone

from .models import Order, OrderItem
from apps.catalog.services import check_low_stock


def _require_rh(user):
    if user.role not in ("ADMIN", "GESTIONNAIRE"):
        raise PermissionDenied("Acces reserve RH/Admin")


def _pct_delta(cur, prev):
    if not prev:
        return None
    try:
        return round(((float(cur) - float(prev)) / float(prev)) * 100, 1)
    except (ZeroDivisionError, TypeError):
        return None


@login_required
def export_dashboard_pdf(request):
    """Genere le PDF du dashboard avec KPIs, commandes et top produits."""
    _require_rh(request.user)

    try:
        from xhtml2pdf import pisa
    except ImportError:
        return HttpResponse(
            "xhtml2pdf non installe. Lancez: pip install xhtml2pdf",
            status=500,
        )

    org = request.user.organization
    now = timezone.now()

    period = request.GET.get("period", "30")
    try:
        days = int(period)
    except ValueError:
        days = 30
    start = now - timedelta(days=days)
    start_prev = start - timedelta(days=days)

    qs = Order.objects.filter(organization=org)
    qs_valid = qs.filter(status__in=["VALIDEE", "EN_LIVRAISON", "LIVREE"])

    cur = qs_valid.filter(created_at__gte=start)
    prev = qs_valid.filter(created_at__gte=start_prev, created_at__lt=start)

    rev_cur = cur.aggregate(s=Sum("total_amount"))["s"] or 0
    rev_prev = prev.aggregate(s=Sum("total_amount"))["s"] or 0
    avg_cur = cur.aggregate(a=Avg("total_amount"))["a"] or 0
    avg_prev = prev.aggregate(a=Avg("total_amount"))["a"] or 0

    kpis = {
        "revenue": {"value": rev_cur, "delta": _pct_delta(rev_cur, rev_prev)},
        "orders": {"value": cur.count(), "delta": _pct_delta(cur.count(), prev.count())},
        "avg_basket": {"value": avg_cur, "delta": _pct_delta(avg_cur, avg_prev)},
        "pending": qs.filter(status="EN_ATTENTE_VALIDATION").count(),
    }

    orders = list(
        qs.filter(created_at__gte=start)
        .select_related("member")
        .order_by("-created_at")[:200]
    )

    top = list(
        OrderItem.objects.filter(
            order__organization=org,
            order__status__in=["VALIDEE", "EN_LIVRAISON", "LIVREE"],
            order__created_at__gte=start,
        )
        .values("product__name")
        .annotate(qty=Sum("quantity"))
        .order_by("-qty")[:5]
    )
    top_products = [{"name": p["product__name"], "qty": p["qty"] or 0} for p in top]

    html = render_to_string("admin/dashboard_pdf.html", {
        "organization": org,
        "kpis": kpis,
        "orders": orders,
        "top_products": top_products,
        "low_stock": check_low_stock(org),
        "period": days,
        "period_start": start.strftime("%d/%m/%Y"),
        "period_end": now.strftime("%d/%m/%Y"),
        "generated_at": now.strftime("%d/%m/%Y %H:%M"),
    })

    buf = BytesIO()
    pisa.CreatePDF(html, dest=buf, encoding="utf-8")
    buf.seek(0)

    resp = HttpResponse(buf.read(), content_type="application/pdf")
    resp["Content-Disposition"] = (
        f'attachment; filename="dashboard-{org.slug}-{now.strftime("%Y%m%d")}.pdf"'
    )
    return resp
