"""Vues du module Demande d'Achat."""
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count, Sum, Q
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import (
    PurchaseRequest, PurchaseRequestItem, DAItem, DACategory,
    DASignature, DASignatureFlow, DAOtpCode, DAStockMovement,
)
from . import workflow
from .dashboard_view import da_dashboard
from .services import (
    create_signature, generate_otp_code, hash_otp_code,
    send_otp_sms, verify_signature,
)


# ═══════════════════════════════════════════════════════════════
# HELPERS PERMISSIONS
# ═══════════════════════════════════════════════════════════════
def da_visa(request, request_id):
    """Visa DA : GET affiche la page, POST traite le visa."""
    from django.shortcuts import get_object_or_404, render, redirect
    from django.contrib import messages
    from django.core.exceptions import PermissionDenied, ValidationError
    from apps.da.models import PurchaseRequest
    from apps.da import workflow

    da = get_object_or_404(
        PurchaseRequest,
        id=request_id,
        organization=request.user.organization,
    )
    user = request.user

    # Analyse du stock (utile pour GET et pour POST des achats)
    stock_analysis = []
    for line in da.items.all():
        available = line.item.stock_quantity or 0
        to_buy = max(0, line.quantity - available)
        stock_analysis.append({
            "item": line.item,
            "quantity": line.quantity,
            "available": available,
            "to_buy": to_buy,
            "unit_price": line.unit_price,
        })

    # Determination des droits
    is_achats_user = _is_achats(user)
    is_director_user = _can_validate_da(user, da)

    can_visa = (
        (is_achats_user and da.status in ("VISEE_DIRECTEUR", "STOCK_VERIFIE")) or
        (is_director_user and da.status == "SOUMISE")
    )

    # GET : afficher la page
    if request.method == "GET":
        return render(request, "da/da_visa_page.html", {
            "da": da,
            "stock_analysis": stock_analysis,
            "is_achats": is_achats_user,
            "is_director": is_director_user,
            "can_visa": can_visa,
        })

    # POST : traiter le visa
    approved = request.POST.get("approved") == "yes"
    comment = request.POST.get("comment", "").strip()

    try:
        if is_achats_user and da.status in ("VISEE_DIRECTEUR", "STOCK_VERIFIE"):
            # 1. Verifier le stock si pas encore fait
            if da.status == "VISEE_DIRECTEUR":
                analysis = {}
                for line in da.items.all():
                    analysis[str(line.item_id)] = {
                        "available": line.item.stock_quantity or 0,
                        "to_buy": max(0, line.quantity - (line.item.stock_quantity or 0)),
                    }
                workflow.verify_stock(da, actor=user, stock_analysis=analysis)
                da.refresh_from_db()

            # 2. Apposer le visa des Achats
            workflow.visa_by_achats(da, actor=user, comment=comment, approved=approved)

            if approved:
                messages.success(
                    request,
                    f"Stock verifie et visa des Achats accorde pour {da.number}."
                )
            else:
                messages.warning(request, f"DA {da.number} refusee par les Achats.")

        elif is_director_user and da.status == "SOUMISE":
            workflow.visa_by_director(da, actor=user, comment=comment, approved=approved)
            if approved:
                messages.success(request, f"Visa Directeur accorde pour {da.number}.")
            else:
                messages.warning(request, f"DA {da.number} refusee par le Directeur.")
        else:
            messages.error(
                request,
                f"Action impossible : statut={da.status}, "
                f"is_achats={is_achats_user}, is_director={is_director_user}"
            )
            return redirect("da_detail", request_id=da.id)

    except ValidationError as e:
        messages.error(request, str(e))

    return redirect("da_detail", request_id=da.id)


def da_sign_page(request, request_id):
    """Page de signature simplifiee pour le DG (sans OTP obligatoire pour demo)."""
    from django.shortcuts import get_object_or_404, render, redirect
    from django.contrib import messages
    from django.core.exceptions import PermissionDenied
    from apps.da.models import PurchaseRequest

    da = get_object_or_404(
        PurchaseRequest,
        id=request_id,
        organization=request.user.organization,
    )

    # Verification des droits
    is_dg = getattr(request.user, "is_dg", False) or request.user.role == "ADMIN"
    if not is_dg:
        raise PermissionDenied("Seul le DG peut signer.")

    # Verification du statut
    if da.status not in ("VISEE_ACHATS", "STOCK_VERIFIE", "VISEE_DIRECTEUR"):
        messages.error(request, f"Cette DA ne peut pas etre signee (statut : {da.get_status_display()}).")
        return redirect("da_detail", request_id=da.id)

    # Si c'est un POST : valider directement
    if request.method == "POST":
        from apps.da import workflow
        comment = request.POST.get("comment", "").strip() or "Signature DG"
        try:
            workflow.validate_da(da, actor=request.user, comment=comment)
            messages.success(request, f"DA {da.number} signee et validee avec succes !")
            return redirect("da_detail", request_id=da.id)
        except Exception as e:
            messages.error(request, f"Erreur : {e}")
            return redirect("da_detail", request_id=da.id)

    # GET : afficher la page de confirmation
    return render(request, "da/sign_confirm.html", {"da": da})


def da_sign_verify(request, request_id):
    """Ancienne route redirigee vers da_sign_page (compatibilite)."""
    return da_sign_page(request, request_id)


def da_sign_refuse(request, request_id):
    """Refus de signature : passe la DA en REFUSEE."""
    from django.shortcuts import get_object_or_404, redirect
    from django.contrib import messages
    from apps.da.models import PurchaseRequest
    from apps.da import workflow

    da = get_object_or_404(PurchaseRequest, id=request_id, organization=request.user.organization)

    if not (getattr(request.user, "is_dg", False) or request.user.role == "ADMIN"):
        raise PermissionDenied("Seul le DG peut refuser.")

    comment = request.POST.get("comment", "").strip() or "Refusee par le DG"
    da.status = "REFUSEE"
    da.rejection_reason = comment
    da.save()
    messages.warning(request, f"DA {da.number} refusee.")
    return redirect("da_detail", request_id=da.id)


def _is_achats(user):
    """Verifie si l'utilisateur fait partie de la Direction des Achats."""
    # DG et ADMIN : toujours OK
    if getattr(user, "is_dg", False) or user.role == "ADMIN":
        return True

    # Si le user est directeur des achats (direction "Achats")
    if getattr(user, "is_director", False):
        for direction in user.directed_directions.all():
            if direction.is_achats or "achat" in direction.name.lower():
                return True

    # Si le service du user depend d'une direction "Achats"
    if user.service and user.service.direction:
        if user.service.direction.is_achats or "achat" in user.service.direction.name.lower():
            return True

    # Fallback : email contenant "achats"
    if "achat" in user.email.lower():
        return True

    return False


def _can_validate_da(user, da):
    """Le user peut-il viser/valider cette DA ?"""
    if user.is_dg:
        return True
    if user.is_director and user.directed_directions.filter(
        id=da.service.direction_id if da.service else None
    ).exists():
        return True
    if _is_achats(user):
        return True
    return False


# ═══════════════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════════════
@login_required
def da_dashboard_old(request):
    """Tableau de bord DA."""
    org = request.user.organization

    # Mes DA
    my_requests = PurchaseRequest.objects.filter(
        organization=org, requester=request.user,
    ).order_by("-created_at")

    # DA en attente de mon action
    pending_signatures = DASignatureFlow.objects.filter(
        purchase_request__organization=org,
        assigned_to=request.user,
        status="PENDING",
    ).select_related("purchase_request")

    # Stats globales
    stats = {
        "total": PurchaseRequest.objects.filter(organization=org).count(),
        "my_total": my_requests.count(),
        "pending_me": pending_signatures.count(),
        "in_progress": PurchaseRequest.objects.filter(
            organization=org,
            status__in=["SOUMISE", "VISEE_DIRECTEUR", "STOCK_VERIFIE", "VALIDEE", "COMMANDEE"],
        ).count(),
        "completed_this_month": PurchaseRequest.objects.filter(
            organization=org,
            status="CLOTUREE",
            created_at__gte=timezone.now() - timedelta(days=30),
        ).count(),
    }

    context = {
        "my_requests": my_requests[:10],
        "pending_signatures": pending_signatures[:10],
        "stats": stats,
    }
    return render(request, "da/dashboard.html", context)


# ═══════════════════════════════════════════════════════════════
# LISTE
# ═══════════════════════════════════════════════════════════════
@login_required
def da_list(request):
    """Liste des DA."""
    org = request.user.organization

    status_filter = request.GET.get("status", "")
    scope = request.GET.get("scope", "all")

    qs = PurchaseRequest.objects.filter(organization=org)

    if scope == "mine":
        qs = qs.filter(requester=request.user)
    elif scope == "pending":
        qs = qs.filter(status__in=["SOUMISE", "VISEE_DIRECTEUR", "STOCK_VERIFIE"])

    if status_filter:
        qs = qs.filter(status=status_filter)

    qs = qs.select_related("requester", "service").order_by("-created_at")

    return render(request, "da/request_list.html", {
        "requests": qs[:200],
        "status_filter": status_filter,
        "scope": scope,
        "statuses": PurchaseRequest.STATUS_CHOICES,
    })


# ═══════════════════════════════════════════════════════════════
# CREATION
# ═══════════════════════════════════════════════════════════════
@login_required
def da_create(request):
    """Cree une nouvelle DA."""
    org = request.user.organization

    if request.method == "POST":
        purpose = request.POST.get("purpose", "").strip()
        priority = request.POST.get("priority", "NORMALE")
        service_id = request.POST.get("service")

        if not purpose:
            messages.error(request, "Le motif est obligatoire.")
            return redirect("da_create")

        from apps.organizations.models import Service
        service = None
        if service_id:
            service = Service.objects.filter(id=service_id, organization=org).first()

        if not service and request.user.service:
            service = request.user.service

        da = workflow.create_purchase_request(
            requester=request.user,
            service=service,
            purpose=purpose,
            priority=priority,
        )

        # Ajouter les lignes
        item_ids = request.POST.getlist("item_id[]")
        quantities = request.POST.getlist("quantity[]")

        for item_id, qty in zip(item_ids, quantities):
            if not item_id or not qty:
                continue
            try:
                item = DAItem.objects.get(id=item_id, organization=org)
                workflow.add_item_to_request(da, item, int(qty))
            except Exception as e:
                messages.warning(request, f"Erreur sur un article : {e}")

        messages.success(request, f"DA {da.number} creee en brouillon.")
        return redirect("da_detail", request_id=da.id)

    # GET
    categories = DACategory.objects.filter(organization=org, is_active=True)
    items = DAItem.objects.filter(
        organization=org, is_active=True,
    ).select_related("category")

    from apps.organizations.models import Service
    services = Service.objects.filter(organization=org, is_active=True)

    return render(request, "da/request_form.html", {
        "categories": categories,
        "items": items,
        "services": services,
    })


# ═══════════════════════════════════════════════════════════════
# DETAIL
# ═══════════════════════════════════════════════════════════════
@login_required
def da_detail(request, request_id):
    """Detail d'une DA avec boutons d'action selon le role."""
    from .models import PurchaseRequest
    from .views import _is_achats, _can_validate_da

    da = get_object_or_404(
        PurchaseRequest.objects.select_related("requester", "service", "validated_by"),
        id=request_id,
        organization=request.user.organization,
    )
    lines = da.items.select_related("item", "item__category")
    history = da.history.select_related("actor")
    signatures = da.signatures.select_related("signer")
    flow = da.signature_flow.select_related("assigned_to")

    # Actions disponibles
    can_edit = da.is_editable and da.requester_id == request.user.id
    can_submit = da.is_editable and da.requester_id == request.user.id
    can_visa = (
        da.status == "SOUMISE"
        and request.user.is_director
        and da.service
        and da.service.direction_id in getattr(request.user, "directed_directions", type("x", (), {"values_list": lambda *a, **k: []})()).values_list("id", flat=True)
    )

    # Boutons d'action par role
    is_achats_user = _is_achats(request.user)
    is_director_user = getattr(request.user, "is_director", False)
    is_dg_user = getattr(request.user, "is_dg", False) or request.user.role == "ADMIN"

    can_visa_director = is_director_user and da.status == "SOUMISE" and _can_validate_da(request.user, da)
    can_visa_achats = is_achats_user and da.status in ("VISEE_DIRECTEUR", "STOCK_VERIFIE")
    can_sign_dg = is_dg_user and da.status == "VISEE_ACHATS"
    can_validate_dg = is_dg_user and da.status == "STOCK_VERIFIE"

    context = {
        "da": da,
        "lines": lines,
        "history": history,
        "signatures": signatures,
        "flow": flow,
        "can_edit": can_edit,
        "can_submit": can_submit,
        "can_visa": can_visa,
        "can_visa_director": can_visa_director,
        "can_visa_achats": can_visa_achats,
        "can_sign_dg": can_sign_dg,
        "can_validate_dg": can_validate_dg,
    }
    return render(request, "da/request_detail.html", context)


def da_submit(request, request_id):
    da = get_object_or_404(PurchaseRequest, id=request_id, organization=request.user.organization)

    if da.requester_id != request.user.id:
        raise PermissionDenied("Seul le demandeur peut soumettre.")

    try:
        workflow.submit_request(da, actor=request.user)
        messages.success(request, f"DA {da.number} soumise au visa.")
    except ValidationError as e:
        messages.error(request, str(e))

    return redirect("da_detail", request_id=da.id)


# ═══════════════════════════════════════════════════════════════
# VISA DIRECTEUR
# ═══════════════════════════════════════════════════════════════
@login_required
@require_POST


def da_verify_stock(request, request_id):
    da = get_object_or_404(PurchaseRequest, id=request_id, organization=request.user.organization)

    if not _is_achats(request.user):
        raise PermissionDenied("Reserve a la Direction des Achats.")

    if request.method == "POST":
        analysis = {}
        for line in da.items.all():
            key = str(line.item_id)
            available = line.item.stock_quantity
            to_buy = max(0, line.quantity - available)
            analysis[key] = {"available": available, "to_buy": to_buy}

        try:
            workflow.verify_stock(da, actor=request.user, stock_analysis=analysis)
            messages.success(request, f"Stock verifie pour {da.number}.")
        except ValidationError as e:
            messages.error(request, str(e))

        return redirect("da_detail", request_id=da.id)

    return render(request, "da/stock_verify.html", {"da": da, "lines": da.items.select_related("item")})


# ═══════════════════════════════════════════════════════════════
# SIGNATURE DG (avec OTP)
# ═══════════════════════════════════════════════════════════════
@login_required


def da_order(request, request_id):
    da = get_object_or_404(PurchaseRequest, id=request_id, organization=request.user.organization)
    if not _is_achats(request.user):
        raise PermissionDenied()

    supplier = request.POST.get("supplier_name", "").strip()
    try:
        workflow.mark_as_ordered(da, actor=request.user, supplier_name=supplier)
        messages.success(request, "DA marquee comme commandee.")
    except ValidationError as e:
        messages.error(request, str(e))

    return redirect("da_detail", request_id=da.id)


@login_required
@require_POST
def da_receive(request, request_id):
    da = get_object_or_404(PurchaseRequest, id=request_id, organization=request.user.organization)
    if not _is_achats(request.user):
        raise PermissionDenied()

    received = {}
    for line in da.items.all():
        qty = request.POST.get(f"received_{line.id}", "0")
        try:
            received[str(line.id)] = int(qty)
        except ValueError:
            pass

    try:
        workflow.receive_items(da, actor=request.user, received_lines=received)
        messages.success(request, "Reception enregistree.")
    except ValidationError as e:
        messages.error(request, str(e))

    return redirect("da_detail", request_id=da.id)


@login_required
@require_POST
def da_close(request, request_id):
    da = get_object_or_404(PurchaseRequest, id=request_id, organization=request.user.organization)
    if not _is_achats(request.user):
        raise PermissionDenied()

    try:
        workflow.close_request(da, actor=request.user)
        messages.success(request, "DA cloturee.")
    except ValidationError as e:
        messages.error(request, str(e))

    return redirect("da_detail", request_id=da.id)


# ═══════════════════════════════════════════════════════════════
# VERIFICATION PUBLIQUE (pas de login)
# ═══════════════════════════════════════════════════════════════
def verify_signature_public(request, signature_hash):
    """Page publique de verification d'une signature."""
    result = verify_signature(signature_hash)
    return render(request, "da/verify.html", {"result": result, "hash": signature_hash})


# ═══════════════════════════════════════════════════════════════
# CATALOGUE ARTICLES (vue rapide)
# ═══════════════════════════════════════════════════════════════
@login_required
def da_items_catalog(request):
    """Catalogue des articles disponibles."""
    org = request.user.organization
    categories = DACategory.objects.filter(organization=org, is_active=True)
    items = DAItem.objects.filter(
        organization=org, is_active=True,
    ).select_related("category").order_by("category__display_order", "name")

    return render(request, "da/items_catalog.html", {
        "categories": categories,
        "items": items,
    })


# ═══════════════════════════════════════════════════════════════
# DOWNLOAD PDF
# ═══════════════════════════════════════════════════════════════
@login_required
def da_download_pdf(request, request_id):
    """Genere et telecharge le PDF de la DA."""
    from django.http import FileResponse
    from .pdf_service import generate_da_pdf

    da = get_object_or_404(
        PurchaseRequest, id=request_id, organization=request.user.organization,
    )

    pdf = generate_da_pdf(da)
    return FileResponse(
        pdf,
        content_type="application/pdf",
        as_attachment=True,
        filename=f"{da.number}.pdf",
    )


@login_required
def da_preview_pdf(request, request_id):
    """Affiche le PDF inline dans le navigateur."""
    from django.http import FileResponse
    from .pdf_service import generate_da_pdf

    da = get_object_or_404(
        PurchaseRequest, id=request_id, organization=request.user.organization,
    )

    pdf = generate_da_pdf(da)
    return FileResponse(pdf, content_type="application/pdf", as_attachment=False)


# ═══════════════════════════════════════════════════════════════
# PAGE RECEPTION (GET)
# ═══════════════════════════════════════════════════════════════
@login_required
def da_receive_page(request, request_id):
    """Page de reception : saisie des quantites recues."""
    da = get_object_or_404(
        PurchaseRequest, id=request_id, organization=request.user.organization,
    )

    if not _is_achats(request.user):
        raise PermissionDenied("Reserve a la Direction des Achats.")

    if da.status not in ("COMMANDEE", "RECUE_PARTIELLE"):
        messages.error(request, "Cette DA n'est pas en attente de reception.")
        return redirect("da_detail", request_id=da.id)

    lines = da.items.select_related("item", "item__category")

    return render(request, "da/receive.html", {
        "da": da,
        "lines": lines,
    })


# ═══════════════════════════════════════════════════════════════
# PAGE CLOTURE (GET) — confirmation
# ═══════════════════════════════════════════════════════════════
@login_required
def da_close_page(request, request_id):
    """Page de confirmation de cloture."""
    da = get_object_or_404(
        PurchaseRequest, id=request_id, organization=request.user.organization,
    )

    if not _is_achats(request.user):
        raise PermissionDenied("Reserve a la Direction des Achats.")

    if da.status != "RECUE":
        messages.error(request, "Seule une DA receptionnee peut etre cloturee.")
        return redirect("da_detail", request_id=da.id)

    lines = da.items.select_related("item")

    # Verifier que toutes les lignes sont completement recues
    all_received = all(line.is_fully_received for line in lines)

    # Mouvements de stock crees
    from .models import DAStockMovement
    movements = DAStockMovement.objects.filter(
        purchase_request=da,
    ).select_related("item", "actor").order_by("-created_at")

    return render(request, "da/close_confirm.html", {
        "da": da,
        "lines": lines,
        "all_received": all_received,
        "movements": movements,
    })


# ═══════════════════════════════════════════════════════════════
# REFUS SIGNATURE DG
# ═══════════════════════════════════════════════════════════════
@login_required
@require_POST

def da_export_excel_list(request):
    """Export Excel de la liste des DA (avec filtres)."""
    from django.http import HttpResponse
    from .excel_service import export_da_list_excel

    if request.user.role not in ("ADMIN", "GESTIONNAIRE") and not (
        request.user.service and request.user.service.direction.is_achats
    ) and not request.user.is_dg:
        raise PermissionDenied("Reserve aux administrateurs DA.")

    org = request.user.organization

    # Filtres
    status_filter = request.GET.get("status", "")
    direction_id = request.GET.get("direction", "")
    period = request.GET.get("period", "90")
    try:
        days = int(period)
    except ValueError:
        days = 90

    qs = PurchaseRequest.objects.filter(
        organization=org,
        created_at__gte=timezone.now() - timedelta(days=days),
    ).select_related("requester", "service", "service__direction", "validated_by")

    if status_filter:
        qs = qs.filter(status=status_filter)
    if direction_id:
        qs = qs.filter(service__direction_id=direction_id)

    qs = qs.order_by("-created_at")[:5000]

    buf = export_da_list_excel(qs)
    filename = f"DA-{org.slug}-{timezone.now().strftime('%Y%m%d_%H%M')}.xlsx"

    response = HttpResponse(
        buf.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required
def da_export_single_excel(request, request_id):
    """Export Excel d'une seule DA."""
    from django.http import HttpResponse
    from .excel_service import export_single_da_excel

    da = get_object_or_404(
        PurchaseRequest, id=request_id, organization=request.user.organization,
    )

    if da.requester_id != request.user.id and request.user.role not in ("ADMIN", "GESTIONNAIRE") and not (
        request.user.service and request.user.service.direction.is_achats
    ):
        raise PermissionDenied("Acces refuse.")

    buf = export_single_da_excel(da)
    filename = f"{da.number}.xlsx"

    response = HttpResponse(
        buf.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


# ═══════════════════════════════════════════════════════════════
# WORKFLOW : REFUS + ANNULATION
# ═══════════════════════════════════════════════════════════════
@login_required
def da_reject_page(request, request_id):
    """Page de refus avec motif."""
    da = get_object_or_404(
        PurchaseRequest, id=request_id, organization=request.user.organization,
    )

    # Verifier les droits
    can_reject = False
    reason_label = ""

    if da.status == "SOUMISE":
        # Directeur
        if request.user.is_director and da.service and da.service.direction.director_id == request.user.id:
            can_reject = True
            reason_label = "Visa Directeur"
    elif da.status == "VISEE_DIRECTEUR":
        # Achats
        if _is_achats(request.user):
            can_reject = True
            reason_label = "Verification stock"
    elif da.status in ("STOCK_VERIFIE", "VALIDEE"):
        # DG
        if request.user.is_dg:
            can_reject = True
            reason_label = "Signature DG"

    if not can_reject:
        messages.error(request, "Vous ne pouvez pas refuser cette DA a ce stade.")
        return redirect("da_detail", request_id=da.id)

    return render(request, "da/reject.html", {
        "da": da,
        "reason_label": reason_label,
    })


@login_required
@require_POST
def da_reject_confirm(request, request_id):
    """Confirme le refus."""
    da = get_object_or_404(
        PurchaseRequest, id=request_id, organization=request.user.organization,
    )

    reason = (request.POST.get("reason") or "").strip()
    if not reason:
        messages.error(request, "Le motif est obligatoire.")
        return redirect("da_reject_page", request_id=da.id)

    old_status = da.status
    da.status = "REFUSEE"
    da.rejection_reason = reason
    da.validated_by = request.user
    da.validated_at = timezone.now()
    da.save(update_fields=["status", "rejection_reason", "validated_by", "validated_at", "updated_at"])

    from .models import PurchaseRequestHistory
    PurchaseRequestHistory.objects.create(
        request=da,
        from_status=old_status,
        to_status="REFUSEE",
        actor=request.user,
        comment=f"Refus par {request.user.email} : {reason}",
    )

    # Notification
    try:
        from .notification_service import notify_da_rejected
        notify_da_rejected(da, reason, rejected_by=request.user)
    except Exception:
        pass

    messages.warning(request, f"DA {da.number} refusee.")
    return redirect("da_detail", request_id=da.id)


@login_required
def da_cancel_page(request, request_id):
    """Page d'annulation (par le demandeur)."""
    da = get_object_or_404(
        PurchaseRequest, id=request_id, organization=request.user.organization,
    )

    # Conditions : seul le demandeur, sur certaines etapes
    if da.requester_id != request.user.id and request.user.role != "ADMIN":
        raise PermissionDenied("Seul le demandeur peut annuler.")

    if da.status not in ("BROUILLON", "SOUMISE", "VISEE_DIRECTEUR", "STOCK_VERIFIE"):
        messages.error(request, "Cette DA ne peut plus etre annulee.")
        return redirect("da_detail", request_id=da.id)

    return render(request, "da/cancel.html", {"da": da})


@login_required
@require_POST
def da_cancel_confirm(request, request_id):
    """Confirme l'annulation."""
    da = get_object_or_404(
        PurchaseRequest, id=request_id, organization=request.user.organization,
    )

    if da.requester_id != request.user.id and request.user.role != "ADMIN":
        raise PermissionDenied()

    if da.status not in ("BROUILLON", "SOUMISE", "VISEE_DIRECTEUR", "STOCK_VERIFIE"):
        messages.error(request, "Cette DA ne peut plus etre annulee.")
        return redirect("da_detail", request_id=da.id)

    reason = (request.POST.get("reason") or "").strip() or "Annulee par le demandeur"

    old_status = da.status
    da.status = "ANNULEE"
    da.rejection_reason = reason
    da.save(update_fields=["status", "rejection_reason", "updated_at"])

    from .models import PurchaseRequestHistory
    PurchaseRequestHistory.objects.create(
        request=da,
        from_status=old_status,
        to_status="ANNULEE",
        actor=request.user,
        comment=reason,
    )

    messages.warning(request, f"DA {da.number} annulee.")
    return redirect("da_detail", request_id=da.id)
