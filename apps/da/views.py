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
from .services import (
    create_signature, generate_otp_code, hash_otp_code,
    send_otp_sms, verify_signature,
)


# ═══════════════════════════════════════════════════════════════
# HELPERS PERMISSIONS
# ═══════════════════════════════════════════════════════════════
def _is_achats(user):
    """Verifie si user fait partie de la Direction des Achats."""
    if user.role in ("ADMIN",) or user.is_dg:
        return True
    if user.service and user.service.direction.is_achats:
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
def da_dashboard(request):
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
    """Detail d'une DA."""
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
        and da.service.direction.director_id == request.user.id
    )
    can_verify_stock = da.status == "VISEE_DIRECTEUR" and _is_achats(request.user)
    can_sign_dg = (
        da.status in ("STOCK_VERIFIE", "VISEE_DIRECTEUR")
        and request.user.is_dg
        and da.total_amount >= getattr(settings, "DA_THRESHOLD_DG", 2_000_000)
    )
    can_order = da.status in ("VALIDEE", "STOCK_VERIFIE") and _is_achats(request.user)
    can_receive = da.status in ("COMMANDEE", "RECUE_PARTIELLE") and _is_achats(request.user)
    can_close = da.status == "RECUE" and _is_achats(request.user)

    return render(request, "da/request_detail.html", {
        "da": da,
        "lines": lines,
        "history": history,
        "signatures": signatures,
        "flow": flow,
        "can_edit": can_edit,
        "can_submit": can_submit,
        "can_visa": can_visa,
        "can_verify_stock": can_verify_stock,
        "can_sign_dg": can_sign_dg,
        "can_order": can_order,
        "can_receive": can_receive,
        "can_close": can_close,
    })


# ═══════════════════════════════════════════════════════════════
# SOUMETTRE
# ═══════════════════════════════════════════════════════════════
@login_required
@require_POST
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
def da_visa(request, request_id):
    da = get_object_or_404(PurchaseRequest, id=request_id, organization=request.user.organization)

    if not _can_validate_da(request.user, da):
        raise PermissionDenied("Vous ne pouvez pas viser cette DA.")

    approved = request.POST.get("approved") == "yes"
    comment = request.POST.get("comment", "").strip()

    try:
        if approved:
            # Creer une signature
            sig = create_signature(
                purchase_request=da,
                signer=request.user,
                signer_role="DIRECTOR",
                signature_level="PIN_OTP",
                comment=comment or "Visa accorde",
                request=request,
                otp_verified=True,
            )
            workflow.visa_by_director(da, actor=request.user, comment=comment, approved=True)
            messages.success(request, f"Visa accorde pour {da.number}.")
        else:
            workflow.visa_by_director(da, actor=request.user, comment=comment, approved=False)
            messages.warning(request, f"DA {da.number} refusee.")
    except ValidationError as e:
        messages.error(request, str(e))

    return redirect("da_detail", request_id=da.id)


# ═══════════════════════════════════════════════════════════════
# VERIFICATION STOCK (Direction des Achats)
# ═══════════════════════════════════════════════════════════════
@login_required
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
def da_sign_page(request, request_id):
    """Page de signature pour le DG (etape 1 : envoi OTP)."""
    da = get_object_or_404(PurchaseRequest, id=request_id, organization=request.user.organization)

    if not request.user.is_dg:
        raise PermissionDenied("Seul le DG peut signer.")

    if da.status not in ("STOCK_VERIFIE", "VISEE_DIRECTEUR"):
        messages.error(request, "Cette DA n'est pas prete pour la signature.")
        return redirect("da_detail", request_id=da.id)

    flow = DASignatureFlow.objects.filter(
        purchase_request=da, role_required="DG", status="PENDING",
    ).first()

    if not flow:
        messages.error(request, "Aucune etape de signature DG en attente.")
        return redirect("da_detail", request_id=da.id)

    # Etape 1 : Envoyer un OTP
    if request.method == "POST" and request.POST.get("action") == "send_otp":
        if not request.user.phone:
            messages.error(request, "Votre numero de telephone n'est pas renseigne.")
            return redirect("da_sign_page", request_id=da.id)

        code = generate_otp_code()
        from django.conf import settings as _s
        expiry = timezone.now() + timedelta(minutes=getattr(_s, "DA_OTP_EXPIRY_MINUTES", 10))

        DAOtpCode.objects.create(
            user=request.user,
            signature_flow=flow,
            code_hash=hash_otp_code(code),
            sent_to=request.user.phone,
            expires_at=expiry,
        )
        send_otp_sms(request.user, code)
        messages.success(request, f"Code envoye au {request.user.phone}.")
        return redirect("da_sign_verify", request_id=da.id)

    return render(request, "da/sign_start.html", {"da": da, "flow": flow})


@login_required
def da_sign_verify(request, request_id):
    """Etape 2 : saisie du code OTP + signature."""
    da = get_object_or_404(PurchaseRequest, id=request_id, organization=request.user.organization)

    if not request.user.is_dg:
        raise PermissionDenied("Seul le DG peut signer.")

    flow = DASignatureFlow.objects.filter(
        purchase_request=da, role_required="DG", status="PENDING",
    ).first()

    if not flow:
        messages.error(request, "Aucune signature DG en attente.")
        return redirect("da_detail", request_id=da.id)

    if request.method == "POST":
        code = request.POST.get("code", "").strip()
        comment = request.POST.get("comment", "").strip()

        otp = DAOtpCode.objects.filter(
            user=request.user, signature_flow=flow, is_used=False,
        ).order_by("-created_at").first()

        if not otp:
            messages.error(request, "Aucun code actif. Demandez un nouveau code.")
            return redirect("da_sign_page", request_id=da.id)

        if not otp.is_valid:
            messages.error(request, "Code expire ou trop de tentatives.")
            return redirect("da_sign_page", request_id=da.id)

        if hash_otp_code(code) != otp.code_hash:
            otp.attempts += 1
            otp.save(update_fields=["attempts"])
            messages.error(request, f"Code invalide ({otp.attempts}/{otp.max_attempts}).")
            return redirect("da_sign_verify", request_id=da.id)

        # OTP valide -> Creer la signature
        otp.is_used = True
        otp.used_at = timezone.now()
        otp.save()

        sig = create_signature(
            purchase_request=da,
            signer=request.user,
            signer_role="DG",
            signature_level="PIN_OTP",
            comment=comment or "Signature DG",
            request=request,
            otp_verified=True,
        )

        workflow.sign_by_dg(da, actor=request.user, signature=sig, comment=comment)
        messages.success(request, f"DA {da.number} signee et validee !")
        return redirect("da_detail", request_id=da.id)

    return render(request, "da/sign_verify.html", {"da": da, "flow": flow})


# ═══════════════════════════════════════════════════════════════
# COMMANDER + RECEPTION + CLOTURE
# ═══════════════════════════════════════════════════════════════
@login_required
@require_POST
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
def da_sign_refuse(request, request_id):
    """Le DG refuse de signer la DA."""
    da = get_object_or_404(
        PurchaseRequest, id=request_id, organization=request.user.organization,
    )

    if not request.user.is_dg:
        raise PermissionDenied("Seul le DG peut refuser.")

    if da.status not in ("STOCK_VERIFIE", "VISEE_DIRECTEUR"):
        messages.error(request, "Cette DA n'est pas en attente de signature.")
        return redirect("da_detail", request_id=da.id)

    reason = (request.POST.get("reason") or "").strip() or "Refus sans motif"

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
        comment=f"Refus DG : {reason}",
    )

    messages.warning(request, f"DA {da.number} refusee.")
    return redirect("da_detail", request_id=da.id)
