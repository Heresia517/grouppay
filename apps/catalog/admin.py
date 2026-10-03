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
