"""Vues parrainage."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST

from .models import Referral, ReferralCode
from .referral_service import get_or_create_referral_code, get_referral_stats


@login_required
def my_referrals(request):
    user = request.user
    code = get_or_create_referral_code(user)
    stats = get_referral_stats(user)
    referrals = Referral.objects.filter(referrer=user).select_related("referred").order_by("-created_at")[:50]

    base_url = getattr(settings, "SITE_URL", "http://127.0.0.1:8000")
    share_url = f"{base_url}/signup/?ref={code.code}"

    return render(request, "accounts/referrals.html", {
        "code": code, "stats": stats, "referrals": referrals, "share_url": share_url,
    })


@login_required
@require_POST
def regenerate_code(request):
    from .referral_service import generate_referral_code
    user = request.user
    try:
        rc = user.referral_code
        if rc.uses_count > 0:
            messages.error(request, "Code deja utilise, impossible de regenerer.")
            return redirect("my_referrals")
        rc.code = generate_referral_code(user)
        rc.save(update_fields=["code"])
        messages.success(request, f"Nouveau code : {rc.code}")
    except ReferralCode.DoesNotExist:
        get_or_create_referral_code(user)
    return redirect("my_referrals")
