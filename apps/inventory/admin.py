from django.contrib import admin
from .models import (
    AssetCategory, Asset, AssetAssignment, MaintenanceRecord, AssetMovement,
)


@admin.register(AssetCategory)
class AssetCategoryAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "organization", "depreciation_years", "is_active")
    list_filter = ("organization", "is_active")
    search_fields = ("code", "name")


class MaintenanceInline(admin.TabularInline):
    model = MaintenanceRecord
    extra = 0
    readonly_fields = ("created_at",)


class AssetAssignmentInline(admin.TabularInline):
    model = AssetAssignment
    extra = 0
    readonly_fields = ("assigned_at",)


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ("reference", "name", "category", "status", "assigned_to", "purchase_price")
    list_filter = ("organization", "category", "status", "condition")
    search_fields = ("reference", "name", "serial_number", "barcode")
    readonly_fields = ("reference", "created_at", "updated_at", "assigned_at")
    inlines = [AssetAssignmentInline, MaintenanceInline]
    date_hierarchy = "created_at"


@admin.register(AssetAssignment)
class AssetAssignmentAdmin(admin.ModelAdmin):
    list_display = ("asset", "assigned_to", "assigned_at", "returned_at")
    list_filter = ("asset__organization",)


@admin.register(MaintenanceRecord)
class MaintenanceRecordAdmin(admin.ModelAdmin):
    list_display = ("asset", "type", "date", "cost", "performed_by")
    list_filter = ("type", "asset__organization")
    date_hierarchy = "date"


@admin.register(AssetMovement)
class AssetMovementAdmin(admin.ModelAdmin):
    list_display = ("asset", "from_status", "to_status", "from_location", "to_location", "created_at")
    readonly_fields = ("created_at",)
