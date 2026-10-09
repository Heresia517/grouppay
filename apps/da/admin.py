from django.contrib import admin
from django.utils import timezone

from .models import (
    DACategory, DAItem, PurchaseRequest, PurchaseRequestItem,
    PurchaseRequestHistory, DAStockMovement,
    DASignature, DASignatureFlow, DAOtpCode,
)


@admin.register(DACategory)
class DACategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "display_order", "is_active")
    list_filter = ("organization", "is_active")
    search_fields = ("name",)


@admin.register(DAItem)
class DAItemAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "unit", "unit_price", "stock_quantity", "reorder_level", "is_active")
    list_filter = ("organization", "category", "is_active", "unit")
    search_fields = ("name", "reference")
    list_editable = ("is_active",)


class PurchaseRequestItemInline(admin.TabularInline):
    model = PurchaseRequestItem
    extra = 0


class PurchaseRequestHistoryInline(admin.TabularInline):
    model = PurchaseRequestHistory
    extra = 0
    readonly_fields = ("from_status", "to_status", "actor", "comment", "created_at")
    can_delete = False


@admin.register(PurchaseRequest)
class PurchaseRequestAdmin(admin.ModelAdmin):
    list_display = ("number", "requester", "department", "status", "priority", "total_amount", "created_at")
    list_filter = ("organization", "status", "priority", "department")
    search_fields = ("number", "requester__email")
    readonly_fields = ("number", "created_at", "updated_at", "validated_at", "ordered_at", "received_at")
    inlines = [PurchaseRequestItemInline, PurchaseRequestHistoryInline]
    date_hierarchy = "created_at"


@admin.register(PurchaseRequestHistory)
class PurchaseRequestHistoryAdmin(admin.ModelAdmin):
    list_display = ("request", "from_status", "to_status", "actor", "created_at")
    list_filter = ("to_status",)
    readonly_fields = ("request", "from_status", "to_status", "actor", "comment", "created_at")

    def has_add_permission(self, request):
        return False


@admin.register(DAStockMovement)
class DAStockMovementAdmin(admin.ModelAdmin):
    list_display = ("item", "movement_type", "quantity", "stock_before", "stock_after", "actor", "created_at")
    list_filter = ("movement_type", "organization")
    readonly_fields = ("created_at",)

    def has_add_permission(self, request):
        return False


@admin.register(DASignature)
class DASignatureAdmin(admin.ModelAdmin):
    list_display = ("signer_role", "signer", "purchase_request", "signed_at", "is_revoked")
    list_filter = ("signer_role", "signature_level", "is_revoked", "organization")
    search_fields = ("signer__email", "signature_hash")
    readonly_fields = (
        "signature_hash", "document_hash", "signed_at",
        "signed_ip", "signed_user_agent", "otp_verified_at", "revoked_at",
    )
    date_hierarchy = "signed_at"

    def has_add_permission(self, request):
        return False


@admin.register(DASignatureFlow)
class DASignatureFlowAdmin(admin.ModelAdmin):
    list_display = ("purchase_request", "step_order", "role_required", "status", "assigned_to")
    list_filter = ("status", "role_required")


@admin.register(DAOtpCode)
class DAOtpCodeAdmin(admin.ModelAdmin):
    list_display = ("user", "signature_flow", "sent_to", "attempts", "is_used", "created_at")
    list_filter = ("is_used",)
    readonly_fields = ("code_hash", "created_at", "used_at", "expires_at")

    def has_add_permission(self, request):
        return False
