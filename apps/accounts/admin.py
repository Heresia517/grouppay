from django.contrib import admin
from .models import User

admin.site.register(User)



from .models import Referral, ReferralCode


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ("referrer", "referred", "status", "reward_amount", "created_at")
    list_filter = ("status", "organization")
    search_fields = ("referrer__email", "referred__email")


@admin.register(ReferralCode)
class ReferralCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "user", "uses_count", "max_uses", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "user__email")
