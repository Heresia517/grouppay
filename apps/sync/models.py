import uuid
from django.db import models


class SyncOperation(models.Model):
    """File d'attente des opérations à pousser vers le serveur central."""
    OP_CREATE = "create"
    OP_UPDATE = "update"
    OP_DELETE = "delete"
    OP_CHOICES = [(OP_CREATE, "Create"), (OP_UPDATE, "Update"), (OP_DELETE, "Delete")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client_id = models.CharField(max_length=64, db_index=True)
    model_name = models.CharField(max_length=100, db_index=True)
    object_id = models.CharField(max_length=64, db_index=True)
    operation = models.CharField(max_length=10, choices=OP_CHOICES)
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    synced_at = models.DateTimeField(null=True, blank=True, db_index=True)
    error_message = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["synced_at", "created_at"])]

    def __str__(self):
        return f"{self.operation} {self.model_name}:{self.object_id}"


class SyncState(models.Model):
    """État de synchronisation par installation cliente."""
    client_id = models.CharField(max_length=64, unique=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    last_snapshot_version = models.CharField(max_length=64, blank=True, default="")
    is_online = models.BooleanField(default=False)

    def __str__(self):
        return f"SyncState({self.client_id})"
