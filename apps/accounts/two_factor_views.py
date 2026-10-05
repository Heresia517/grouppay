"""Vues 2FA TOTP (django-otp)."""
import base64
import io

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST

from django_otp import devices_for_user
from django_otp.plugins.otp_totp.models import TOTPDevice


def get_user_totp_device(user):
    """Retourne le device TOTP confirmé de l'user (ou None)."""
    if not user.is_authenticated:
        return None
    for d in devices_for_user(user, confirmed=True):
        if isinstance(d, TOTPDevice):
            return d
    return None


@login_required
def two_factor_setup(request):
    """Écran de configuration 2FA."""
    user = request.user
    device = get_user_totp_device(user)

    # Si déjà configuré, rediriger vers l'état "activé"
    if device and device.confirmed:
        return render(request, "accounts/2fa_enabled.html", {"device": device})

    # Créer ou récupérer un device non confirmé
    unconfirmed = TOTPDevice.objects.filter(user=user, confirmed=False).first()
    if not unconfirmed:
        unconfirmed = TOTPDevice.objects.create(
            user=user, name="GroupPay", confirmed=False,
        )

    # Générer QR code
    qr_url = unconfirmed.config_url

    try:
        import qrcode
        img = qrcode.make(qr_url)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        qr_base64 = base64.b64encode(buf.getvalue()).decode("ascii")
    except ImportError:
        qr_base64 = ""

    return render(request, "accounts/2fa_setup.html", {
        "device": unconfirmed,
        "qr_code": qr_base64,
        "secret": unconfirmed.key,
    })


@login_required
@require_POST
def two_factor_verify(request):
    """Vérifie le code TOTP et confirme le device."""
    user = request.user
    token = (request.POST.get("token") or "").strip().replace(" ", "")

    device = TOTPDevice.objects.filter(user=user, confirmed=False).first()
    if not device:
        messages.error(request, "Aucun appareil 2FA en attente de configuration.")
        return redirect("two_factor_setup")

    if device.verify_token(token):
        device.confirmed = True
        device.save(update_fields=["confirmed"])
        messages.success(request, "✓ 2FA activé avec succès !")
        return redirect("two_factor_setup")

    messages.error(request, "Code invalide. Réessayez.")
    return redirect("two_factor_setup")


@login_required
@require_POST
def two_factor_disable(request):
    """Désactive la 2FA (supprime TOUS les devices, confirmés ou non)."""
    user = request.user
    # Supprimer TOUS les devices TOTP de l'user
    count, _ = TOTPDevice.objects.filter(user=user).delete()
    if count:
        messages.success(request, "2FA désactivé.")
    else:
        messages.info(request, "Aucune 2FA n'était activée.")
    return redirect("two_factor_setup")


@login_required
def two_factor_status(request):
    """Renvoie le statut 2FA (JSON)."""
    device = get_user_totp_device(request.user)
    return JsonResponse({"enabled": bool(device and device.confirmed)})
