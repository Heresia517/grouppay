"""Service de notifications DA enrichies (email + SMS + in-app)."""
from django.conf import settings
from django.utils import timezone


def _get_default_context(purchase_request):
    """Contexte de base pour toutes les notifications."""
    org = purchase_request.organization
    base_url = getattr(settings, "SITE_URL", "http://127.0.0.1:8000")
    return {
        "organization": org,
        "color_primary": org.color_primary,
        "color_secondary": org.color_secondary,
        "da_number": purchase_request.number,
        "da_amount": f"{purchase_request.total_amount:,.0f}".replace(",", " "),
        "da_currency": purchase_request.currency_code,
        "da_url": f"{base_url}/da/requests/{purchase_request.id}/",
        "requester_email": purchase_request.requester.email,
        "service_name": purchase_request.service.name if purchase_request.service else "—",
    }


def _notify_in_app(user, title, body, action_url=""):
    """Notification in-app."""
    try:
        from apps.notifications.models import Notification
        Notification.objects.create(
            organization=user.organization,
            recipient=user,
            channel="IN_APP",
            title=title,
            body=body,
            is_read=False,
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"In-app notif failed: {e}")


def _send_email(user, subject, template_name, context):
    """Email HTML."""
    if not user.email:
        return False
    try:
        from apps.notifications.email_service import send_email
        return send_email(
            recipient_email=user.email,
            subject=subject,
            template_name=template_name,
            context=context,
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Email failed: {e}")
        return False


def _send_sms(user, message):
    """SMS court."""
    if not user.phone:
        return False
    try:
        from apps.notifications.sms_service import send_sms
        return send_sms(user.phone, message)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"SMS failed: {e}")
        return False


# ═══════════════════════════════════════════════════════════════
# 1. DA SOUMISE → notifier Directeur
# ═══════════════════════════════════════════════════════════════
def notify_da_submitted(purchase_request, director):
    """Envoi au Directeur pour visa."""
    if not director:
        return

    ctx = _get_default_context(purchase_request)
    ctx["director_email"] = director.email

    _notify_in_app(
        director,
        f"DA à viser : {purchase_request.number}",
        f"Une DA de {purchase_request.requester.email} attend votre visa.",
        ctx["da_url"],
    )
    _send_email(
        director,
        f"📋 DA à viser : {purchase_request.number}",
        "emails/da_submitted.html",
        ctx,
    )
    _send_sms(
        director,
        f"GroupPay: DA {purchase_request.number} a viser. {ctx['da_amount']} {ctx['da_currency']}",
    )


# ═══════════════════════════════════════════════════════════════
# 2. DA VISÉE → notifier Achats + retour demandeur
# ═══════════════════════════════════════════════════════════════
def notify_da_visa_approved(purchase_request, achats_director):
    """Visa accordé → Achats + demandeur."""
    ctx = _get_default_context(purchase_request)

    # Direction des Achats
    if achats_director:
        _notify_in_app(
            achats_director,
            f"DA visée à vérifier : {purchase_request.number}",
            f"La DA de {purchase_request.requester.email} attend la vérification stock.",
            ctx["da_url"],
        )
        _send_email(
            achats_director,
            f"🔍 DA à vérifier : {purchase_request.number}",
            "emails/da_to_verify.html",
            ctx,
        )
        _send_sms(
            achats_director,
            f"GroupPay: DA {purchase_request.number} a verifier (stock).",
        )

    # Demandeur
    _notify_in_app(
        purchase_request.requester,
        f"DA visée : {purchase_request.number}",
        "Votre DA a été visée par votre Directeur et transmise aux Achats.",
        ctx["da_url"],
    )
    _send_email(
        purchase_request.requester,
        f"✓ DA visée : {purchase_request.number}",
        "emails/da_visa_ok.html",
        ctx,
    )


# ═══════════════════════════════════════════════════════════════
# 3. DA REFUSÉE
# ═══════════════════════════════════════════════════════════════
def notify_da_rejected(purchase_request, reason, rejected_by=None):
    """Refus (Directeur, Achats ou DG)."""
    ctx = _get_default_context(purchase_request)
    ctx["reason"] = reason or "Non précisé"
    ctx["rejected_by"] = rejected_by.email if rejected_by else "—"

    _notify_in_app(
        purchase_request.requester,
        f"DA refusée : {purchase_request.number}",
        f"Motif : {reason}",
        ctx["da_url"],
    )
    _send_email(
        purchase_request.requester,
        f"✗ DA refusée : {purchase_request.number}",
        "emails/da_rejected.html",
        ctx,
    )
    _send_sms(
        purchase_request.requester,
        f"GroupPay: DA {purchase_request.number} REFUSEE. Motif: {reason[:60]}",
    )


# ═══════════════════════════════════════════════════════════════
# 4. STOCK VÉRIFIÉ → notifier DG (si requis)
# ═══════════════════════════════════════════════════════════════
def notify_da_stock_verified(purchase_request, dg=None, needs_purchase=False):
    """Stock vérifié → DG si nécessaire, sinon Achats."""
    ctx = _get_default_context(purchase_request)

    if needs_purchase and dg:
        _notify_in_app(
            dg,
            f"DA à signer : {purchase_request.number}",
            f"Achat externe requis. Montant : {ctx['da_amount']} {ctx['da_currency']}",
            ctx["da_url"],
        )
        _send_email(
            dg,
            f"✍️ DA à signer : {purchase_request.number}",
            "emails/da_to_sign.html",
            ctx,
        )
        _send_sms(
            dg,
            f"GroupPay: DA {purchase_request.number} a signer ({ctx['da_amount']} {ctx['da_currency']})",
        )
    else:
        _notify_in_app(
            purchase_request.requester,
            f"DA stock vérifié : {purchase_request.number}",
            "Tout le stock est disponible. Votre DA passe en commande.",
            ctx["da_url"],
        )


# ═══════════════════════════════════════════════════════════════
# 5. DA VALIDÉE (signée DG) → notifier demandeur + Achats
# ═══════════════════════════════════════════════════════════════
def notify_da_validated(purchase_request, achats_director=None):
    """Signature DG OK → tout le monde."""
    ctx = _get_default_context(purchase_request)

    _notify_in_app(
        purchase_request.requester,
        f"DA validée : {purchase_request.number}",
        f"Signée par le DG. Traitement en cours par les Achats.",
        ctx["da_url"],
    )
    _send_email(
        purchase_request.requester,
        f"✓ DA validée : {purchase_request.number}",
        "emails/da_validated.html",
        ctx,
    )
    _send_sms(
        purchase_request.requester,
        f"GroupPay: DA {purchase_request.number} VALIDEE par le DG.",
    )

    if achats_director:
        _notify_in_app(
            achats_director,
            f"DA validée à commander : {purchase_request.number}",
            f"Le DG a signé. Procéder à la commande.",
            ctx["da_url"],
        )


# ═══════════════════════════════════════════════════════════════
# 6. DA COMMANDÉE → notifier demandeur
# ═══════════════════════════════════════════════════════════════
def notify_da_ordered(purchase_request, supplier_name=""):
    """Commande passée → demandeur."""
    ctx = _get_default_context(purchase_request)
    ctx["supplier"] = supplier_name or "—"

    _notify_in_app(
        purchase_request.requester,
        f"DA commandée : {purchase_request.number}",
        f"Commande passée chez {supplier_name}." if supplier_name else "Commande en cours.",
        ctx["da_url"],
    )
    _send_email(
        purchase_request.requester,
        f"📦 DA commandée : {purchase_request.number}",
        "emails/da_ordered.html",
        ctx,
    )


# ═══════════════════════════════════════════════════════════════
# 7. DA RECEPTIONNÉE → notifier demandeur
# ═══════════════════════════════════════════════════════════════
def notify_da_received(purchase_request):
    """Réception OK → demandeur peut venir chercher."""
    ctx = _get_default_context(purchase_request)

    _notify_in_app(
        purchase_request.requester,
        f"DA réceptionnée : {purchase_request.number}",
        "Vos articles sont disponibles au magasin.",
        ctx["da_url"],
    )
    _send_email(
        purchase_request.requester,
        f"🎉 DA réceptionnée : {purchase_request.number}",
        "emails/da_received.html",
        ctx,
    )
    _send_sms(
        purchase_request.requester,
        f"GroupPay: DA {purchase_request.number} receptionnee. Retrait au magasin.",
    )


# ═══════════════════════════════════════════════════════════════
# 8. DA CLÔTURÉE
# ═══════════════════════════════════════════════════════════════
def notify_da_closed(purchase_request):
    """Clôture → demandeur + récap."""
    ctx = _get_default_context(purchase_request)

    _notify_in_app(
        purchase_request.requester,
        f"DA clôturée : {purchase_request.number}",
        "Votre DA est terminée.",
        ctx["da_url"],
    )
    _send_email(
        purchase_request.requester,
        f"✓ DA clôturée : {purchase_request.number}",
        "emails/da_closed.html",
        ctx,
    )
