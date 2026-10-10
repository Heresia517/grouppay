from django.contrib import admin
from .models import Notification

admin.site.register(Notification)



from .models import PushSubscription


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "is_active", "created_at", "last_used_at")
    list_filter = ("is_active",)
    search_fields = ("user__email", "endpoint")
    readonly_fields = ("endpoint", "p256dh", "auth", "created_at", "last_used_at")
