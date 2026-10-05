from django.contrib import admin
from .models import Category, Product

admin.site.register(Category)
admin.site.register(Product)


from .models import Coupon, WishlistItem


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code", "organization", "discount_type", "discount_value", "is_active", "used_count")
    list_filter = ("organization", "is_active", "discount_type")
    search_fields = ("code",)


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ("user", "product", "organization", "added_at")
    list_filter = ("organization",)



from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "member", "rating", "is_verified_purchase", "is_published", "created_at")
    list_filter = ("rating", "is_published", "is_verified_purchase", "organization")
    search_fields = ("product__name", "member__email", "comment")
    actions = ["publish", "unpublish"]

    def publish(self, request, queryset):
        queryset.update(is_published=True)
    publish.short_description = "Publier les avis"

    def unpublish(self, request, queryset):
        queryset.update(is_published=False)
    unpublish.short_description = "Dépublier les avis"



from .models import StockMovement, StockAlert


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("created_at", "product", "movement_type", "quantity",
                    "stock_before", "stock_after", "actor")
    list_filter = ("movement_type", "organization")
    search_fields = ("product__name", "reason")
    date_hierarchy = "created_at"
    readonly_fields = [f.name for f in StockMovement._meta.fields]

    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False


@admin.register(StockAlert)
class StockAlertAdmin(admin.ModelAdmin):
    list_display = ("created_at", "product", "stock_at_alert", "reorder_level", "is_resolved")
    list_filter = ("is_resolved", "organization")
    actions = ["resolve_alerts"]

    def resolve_alerts(self, request, queryset):
        from django.utils import timezone
        queryset.update(is_resolved=True, resolved_at=timezone.now())
    resolve_alerts.short_description = "Marquer comme résolues"



from .models import ProductRequest, ProductRequestVote


@admin.register(ProductRequest)
class ProductRequestAdmin(admin.ModelAdmin):
    list_display = ("title", "proposed_by", "status", "vote_count", "created_at")
    list_filter = ("status", "organization")
    search_fields = ("title", "description")
    actions = ["mark_accepted", "mark_rejected", "mark_reviewing"]

    def vote_count(self, obj):
        return obj.votes.count()
    vote_count.short_description = "Votes"

    def mark_accepted(self, request, queryset):
        queryset.update(status="ACCEPTED")
    mark_accepted.short_description = "Marquer acceptées"

    def mark_rejected(self, request, queryset):
        queryset.update(status="REJECTED")
    mark_rejected.short_description = "Marquer refusées"

    def mark_reviewing(self, request, queryset):
        queryset.update(status="REVIEWING")
    mark_reviewing.short_description = "Marquer en négociation"


@admin.register(ProductRequestVote)
class ProductRequestVoteAdmin(admin.ModelAdmin):
    list_display = ("request", "member", "created_at")
    list_filter = ("organization",)
