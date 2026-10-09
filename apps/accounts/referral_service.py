"""Service parrainage."""
import secrets
import string
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone


def generate_referral_code(user, length=8):
    from .models import ReferralCode
    prefix = user.email.split("@")[0][:4].upper()
    prefix = "".join(c for c in prefix if c.isalnum()) or "GP"
    for _ in range(20):
        suffix = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(length - len(prefix)))
        code = prefix + suffix
        if not ReferralCode.objects.filter(code=code).exists():
            return code
    return "REF" + secrets.token_hex(4).upper()


def get_or_create_referral_code(user):
    from .models import ReferralCode
    try:
        return user.referral_code
    except ReferralCode.DoesNotExist:
        return ReferralCode.objects.create(user=user, code=generate_referral_code(user))


@transaction.atomic
def apply_referral_code(new_user, code_string):
    from .models import ReferralCode, Referral
    try:
        code = ReferralCode.objects.select_for_update().get(code=code_string.upper().strip(), is_active=True)
    except ReferralCode.DoesNotExist:
        return None, "Code invalide"

    if not code.can_be_used:
        return None, "Code expire ou deja utilise"
    if code.user_id == new_user.id:
        return None, "Vous ne pouvez pas vous parrainer"
    if code.user.organization_id != new_user.organization_id:
        return None, "Code d'une autre organisation"

    reward = Decimal(str(getattr(settings, "REFERRAL_REWARD_AMOUNT", "5000")))

    referral, created = Referral.objects.get_or_create(
        referrer=code.user, referred=new_user,
        defaults={"organization": new_user.organization, "status": "ACTIVE", "reward_amount": reward},
    )

    if created:
        code.uses_count += 1
        code.save(update_fields=["uses_count"])
        new_user.referred_by = code.user
        new_user.save(update_fields=["referred_by"])
        code.user.referral_reward_balance = (code.user.referral_reward_balance or 0) + reward
        code.user.save(update_fields=["referral_reward_balance"])
        referral.status = "REWARDED"
        referral.rewarded_at = timezone.now()
        referral.save(update_fields=["status", "rewarded_at"])

    return referral, None


def get_referral_stats(user):
    from .models import Referral
    qs = Referral.objects.filter(referrer=user)
    return {
        "total_referrals": qs.count(),
        "rewarded_referrals": qs.filter(status="REWARDED").count(),
        "total_earned": sum(r.reward_amount for r in qs.filter(status="REWARDED")),
        "balance": user.referral_reward_balance or 0,
    }
