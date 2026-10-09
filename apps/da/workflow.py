"""Workflow metier du module Demande d'Achat.

Etapes :
  BROUILLON -> SOUMISE -> VISEE_DIRECTEUR -> STOCK_VERIFIE
  -> SIGNEE_DG -> COMMANDEE -> RECUE -> CLOTUREE

Chaque transition est atomique et cree une entree dans PurchaseRequestHistory.
"""
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.notifications.email_service import send_email
from apps.notifications.sms_service import send_sms

from .notification_service import (
    notify_da_submitted, notify_da_visa_approved, notify_da_rejected,
    notify_da_stock_verified, notify_da_validated,
    notify_da_ordered, notify_da_received, notify_da_closed,
)


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════
def generate_da_number(organization):
    """Genere un numero unique : DA-SONABEL-2026-000001."""
    from .models import PurchaseRequest

    year = date.today().year
    prefix = f"DA-{organization.slug.upper()}-{year}-"
    count = PurchaseRequest.objects.filter(
        organization=organization,
        number__startswith=prefix,
    ).count()
    return f"{prefix}{count + 1:06d}"


def _add_history(request_obj, from_status, to_status, actor, comment=""):
    """Ajoute une entree d'historique."""
    from .models import PurchaseRequestHistory
    PurchaseRequestHistory.objects.create(
        request=request_obj,
        from_status=from_status,
        to_status=to_status,
        actor=actor,
        comment=comment,
    )


def _notify(user, subject, body, action_url=""):
    """Notification interne + email (non bloquant)."""
    try:
        from apps.notifications.models import Notification
        Notification.objects.create(
            organization=user.organization,
            recipient=user,
            channel="IN_APP",
            title=subject,
            body=body,
        )
    except Exception:
        pass

    try:
        if user.email:
            send_email(
                recipient_email=user.email,
                subject=subject,
                template_name="emails/da_notification.html",
                context={
                    "organization": user.organization,
                    "title": subject,
                    "body": body,
                    "action_url": action_url,
                },
            )
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════
# 1. CREATION
# ═══════════════════════════════════════════════════════════════
@transaction.atomic
def create_purchase_request(requester, service, purpose, priority="NORMALE"):
    """Cree une DA en brouillon."""
    from .models import PurchaseRequest

    req = PurchaseRequest.objects.create(
        organization=requester.organization,
        number=generate_da_number(requester.organization),
        requester=requester,
        service=service,
        department=service.name if service else "",
        purpose=purpose,
        priority=priority,
        status="BROUILLON",
        currency_code=requester.organization.currency_code,
    )
    _add_history(req, "", "BROUILLON", requester, "Creation de la DA")
    return req


@transaction.atomic
def add_item_to_request(purchase_request, item, quantity, unit_price=None):
    """Ajoute une ligne a une DA."""
    from .models import PurchaseRequestItem

    if purchase_request.status != "BROUILLON":
        raise ValidationError("Impossible de modifier une DA non brouillon.")

    if item.max_per_request and quantity > item.max_per_request:
        raise ValidationError(
            f"Quantite maximale par DA pour {item.name} : {item.max_per_request}"
        )

    unit_price = unit_price or item.unit_price

    line, created = PurchaseRequestItem.objects.update_or_create(
        request=purchase_request,
        item=item,
        defaults={"quantity": quantity, "unit_price": unit_price},
    )
    purchase_request.compute_total()
    return line


# ═══════════════════════════════════════════════════════════════
# 2. SOUMISSION (chef de service -> directeur)
# ═══════════════════════════════════════════════════════════════
@transaction.atomic
def submit_request(purchase_request, actor):
    """Soumet la DA au visa du Directeur de la direction."""
    if purchase_request.status != "BROUILLON":
        raise ValidationError("Seule une DA en brouillon peut etre soumise.")

    if purchase_request.items.count() == 0:
        raise ValidationError("Impossible de soumettre une DA vide.")

    # Creer le workflow de signature
    _create_signature_flow(purchase_request)

    old_status = purchase_request.status
    purchase_request.status = "SOUMISE"
    purchase_request.save(update_fields=["status", "updated_at"])

    _add_history(purchase_request, old_status, "SOUMISE", actor, "Soumission de la DA")

    # Notifier le Directeur (enrichi)
    director = _get_director_for_service(purchase_request.service)
    if director:
        notify_da_submitted(purchase_request, director)

    return purchase_request


def _create_signature_flow(purchase_request):
    """Cree les etapes de signature pour la DA."""
    from .models import DASignatureFlow

    DASignatureFlow.objects.filter(purchase_request=purchase_request).delete()

    # Etape 1 : Directeur de la direction emettrice
    director = _get_director_for_service(purchase_request.service)
    if director:
        DASignatureFlow.objects.create(
            purchase_request=purchase_request,
            step_order=1,
            role_required="DIRECTOR",
            assigned_to=director,
        )

    # Etape 2 : Directeur des Achats (verification stock)
    achats_director = _get_achats_director(purchase_request.organization)
    if achats_director:
        DASignatureFlow.objects.create(
            purchase_request=purchase_request,
            step_order=2,
            role_required="ACHATS_DIRECTOR",
            assigned_to=achats_director,
        )

    # Etape 3 : DG (si montant depasse seuil ou si achat externe)
    from django.conf import settings
    threshold = getattr(settings, "DA_THRESHOLD_DG", 2_000_000)

    if purchase_request.total_amount >= threshold:
        dg = _get_dg(purchase_request.organization)
        if dg:
            DASignatureFlow.objects.create(
                purchase_request=purchase_request,
                step_order=3,
                role_required="DG",
                assigned_to=dg,
            )


def _get_director_for_service(service):
    """Trouve le directeur de la direction du service."""
    if not service:
        return None
    return service.direction.director


def _get_achats_director(organization):
    """Trouve le directeur de la Direction des Achats."""
    from apps.organizations.models import Direction
    d = Direction.objects.filter(
        organization=organization, is_achats=True, is_active=True,
    ).first()
    return d.director if d else None


def _get_dg(organization):
    """Trouve le DG."""
    from apps.accounts.models import User
    return User.objects.filter(
        organization=organization, is_dg=True, is_active=True,
    ).first()


# ═══════════════════════════════════════════════════════════════
# 3. VISA DIRECTEUR
# ═══════════════════════════════════════════════════════════════
@transaction.atomic
def visa_by_director(purchase_request, actor, comment="", approved=True):
    """Visa du Directeur de la direction emettrice."""
    if purchase_request.status != "SOUMISE":
        raise ValidationError("La DA doit etre SOUMISE.")

    if not approved:
        old_status = purchase_request.status
        purchase_request.status = "REFUSEE"
        purchase_request.rejection_reason = comment
        purchase_request.validated_by = actor
        purchase_request.validated_at = timezone.now()
        purchase_request.save()

        _add_history(purchase_request, old_status, "REFUSEE", actor, comment)
        notify_da_rejected(purchase_request, comment, rejected_by=actor)
        return purchase_request

    old_status = purchase_request.status
    purchase_request.status = "VISEE_DIRECTEUR"
    purchase_request.validated_by = actor
    purchase_request.validated_at = timezone.now()
    purchase_request.save()

    _add_history(purchase_request, old_status, "VISEE_DIRECTEUR", actor, comment or "Visa accorde")

    # Notifier la Direction des Achats (enrichi)
    achats_director = _get_achats_director(purchase_request.organization)
    notify_da_visa_approved(purchase_request, achats_director)

    return purchase_request


# ═══════════════════════════════════════════════════════════════
# 4. VERIFICATION STOCK (Direction des Achats)
# ═══════════════════════════════════════════════════════════════
@transaction.atomic
def verify_stock(purchase_request, actor, stock_analysis=None):
    """Verification du stock magasin par la Direction des Achats.

    stock_analysis : dict {item_id: {'available': int, 'to_buy': int}}
    """
    if purchase_request.status != "VISEE_DIRECTEUR":
        raise ValidationError("La DA doit etre visee par le Directeur.")

    stock_analysis = stock_analysis or {}

    # Analyser automatiquement si non fourni
    for line in purchase_request.items.all():
        available = line.item.stock_quantity
        line_analysis = stock_analysis.get(str(line.item_id), {})
        to_buy = line_analysis.get("to_buy", max(0, line.quantity - available))
        line.notes = f"Stock: {available}/{line.quantity} - A acheter: {to_buy}"
        line.save(update_fields=["notes"])

    old_status = purchase_request.status
    purchase_request.status = "STOCK_VERIFIE"
    purchase_request.save()

    _add_history(purchase_request, old_status, "STOCK_VERIFIE", actor, "Stock verifie")

    # Si aucun achat externe necessaire -> cloture directe
    needs_purchase = any(
        int(line.item.stock_quantity) < line.quantity
        for line in purchase_request.items.all()
    )

    if not needs_purchase:
        _add_history(
            purchase_request, "STOCK_VERIFIE", "COMMANDEE", actor,
            "Tout le stock disponible - sortie magasin",
        )
        purchase_request.status = "COMMANDEE"
        purchase_request.ordered_by = actor
        purchase_request.ordered_at = timezone.now()
        purchase_request.save()

    else:
        # Notifier le DG si son visa est requis
        dg = _get_dg(purchase_request.organization)
        from django.conf import settings
        threshold = getattr(settings, "DA_THRESHOLD_DG", 2_000_000)

        if dg and purchase_request.total_amount >= threshold:
            _notify(
                dg,
                f"DA a signer : {purchase_request.number}",
                f"Achat externe requis. Montant : {purchase_request.total_amount} {purchase_request.currency_code}",
                action_url=f"/da/requests/{purchase_request.id}/",
            )

    return purchase_request


# ═══════════════════════════════════════════════════════════════
# 5. SIGNATURE DG
# ═══════════════════════════════════════════════════════════════
@transaction.atomic
def sign_by_dg(purchase_request, actor, signature, comment=""):
    """Signature du DG (cree une DASignature + change le statut)."""
    if purchase_request.status not in ("STOCK_VERIFIE", "VISEE_DIRECTEUR"):
        raise ValidationError("La DA n'est pas prete pour la signature DG.")

    old_status = purchase_request.status
    purchase_request.status = "VALIDEE"
    purchase_request.save()

    _add_history(purchase_request, old_status, "VALIDEE", actor,
                 comment or "Signe par le DG")

    # Update flow step
    from .models import DASignatureFlow
    flow = DASignatureFlow.objects.filter(
        purchase_request=purchase_request,
        role_required="DG",
        status="PENDING",
    ).first()
    if flow:
        flow.status = "SIGNED"
        flow.signature = signature
        flow.save()

    # Notifier le demandeur
    _notify(
        purchase_request.requester,
        f"DA validee : {purchase_request.number}",
        "Votre DA a ete validee par le DG.",
        action_url=f"/da/requests/{purchase_request.id}/",
    )

    return purchase_request


# ═══════════════════════════════════════════════════════════════
# 6. COMMANDE
# ═══════════════════════════════════════════════════════════════
@transaction.atomic
def mark_as_ordered(purchase_request, actor, supplier_name=""):
    """Marque la DA comme commandee."""
    if purchase_request.status not in ("VALIDEE", "STOCK_VERIFIE"):
        raise ValidationError("Statut invalide.")

    old_status = purchase_request.status
    purchase_request.status = "COMMANDEE"
    purchase_request.ordered_by = actor
    purchase_request.ordered_at = timezone.now()
    if supplier_name:
        purchase_request.supplier_name = supplier_name
    purchase_request.save()

    _add_history(purchase_request, old_status, "COMMANDEE", actor,
                 f"Commandee chez {supplier_name}" if supplier_name else "Commandee")

    return purchase_request


# ═══════════════════════════════════════════════════════════════
# 7. RECEPTION
# ═══════════════════════════════════════════════════════════════
@transaction.atomic
def receive_items(purchase_request, actor, received_lines=None):
    """Enregistre la reception des articles et met a jour le stock.

    received_lines : dict {line_id: quantity_received}
    """
    from .models import DAStockMovement

    if purchase_request.status not in ("COMMANDEE", "RECUE_PARTIELLE"):
        raise ValidationError("Statut invalide.")

    received_lines = received_lines or {}
    all_received = True

    for line in purchase_request.items.all():
        qty = received_lines.get(str(line.id), 0)
        if qty > 0:
            line.quantity_received += qty
            line.save(update_fields=["quantity_received"])

            # Mouvement stock
            item = line.item
            stock_before = item.stock_quantity
            item.stock_quantity += qty
            item.save(update_fields=["stock_quantity"])

            DAStockMovement.objects.create(
                organization=purchase_request.organization,
                item=item,
                movement_type="IN",
                quantity=qty,
                stock_before=stock_before,
                stock_after=item.stock_quantity,
                reason=f"Reception DA {purchase_request.number}",
                purchase_request=purchase_request,
                actor=actor,
            )

        if not line.is_fully_received:
            all_received = False

    old_status = purchase_request.status
    new_status = "RECUE" if all_received else "RECUE_PARTIELLE"
    purchase_request.status = new_status
    purchase_request.received_by = actor
    purchase_request.received_at = timezone.now()
    purchase_request.save()

    _add_history(purchase_request, old_status, new_status, actor, "Reception partielle" if not all_received else "Reception complete")

    if all_received:
        _notify(
            purchase_request.requester,
            f"DA receptionnee : {purchase_request.number}",
            "Les articles sont disponibles au magasin.",
            action_url=f"/da/requests/{purchase_request.id}/",
        )

    return purchase_request


# ═══════════════════════════════════════════════════════════════
# 8. CLOTURE
# ═══════════════════════════════════════════════════════════════
@transaction.atomic
def close_request(purchase_request, actor):
    """Cloture la DA."""
    if purchase_request.status != "RECUE":
        raise ValidationError("Seule une DA receptionnee peut etre cloturee.")

    old_status = purchase_request.status
    purchase_request.status = "CLOTUREE"
    purchase_request.save()

    _add_history(purchase_request, old_status, "CLOTUREE", actor, "DA cloturee")
    return purchase_request
