from django.contrib import admin
from .models import SyncOperation, SyncState


@admin.register(SyncOperation)
class SyncOperationAdmin(admin.ModelAdmin):
    list_display = ("created_at", "operation", "model_name", "object_id", "synced_at")
    list_filter = ("operation", "model_name", "synced_at")
    search_fields = ("object_id", "model_name")
    readonly_fields = ("id", "created_at")


@admin.register(SyncState)
class SyncStateAdmin(admin.ModelAdmin):
    list_display = ("client_id", "last_sync_at", "last_snapshot_version", "is_online")
