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
