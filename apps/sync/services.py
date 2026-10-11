import socket
import requests
from django.conf import settings
from django.utils import timezone
from .models import SyncOperation, SyncState


class SyncService:
    """Client de synchronisation push/pull vers le serveur central."""

    def __init__(self, server_url=None, api_key=None):
        self.server_url = (server_url or settings.SYNC_SERVER_URL).rstrip("/")
        self.api_key = api_key or settings.SYNC_API_KEY

    def _state(self):
        s, _ = SyncState.objects.get_or_create(client_id=socket.gethostname())
        return s

    def push_pending(self, batch_size=100):
        pending = list(
            SyncOperation.objects.filter(synced_at__isnull=True)
            .order_by("created_at")[:batch_size]
        )
        if not pending:
            return {"pushed": 0, "failed": 0}

        ops = [{
            "id": str(o.id),
            "client_id": o.client_id,
            "model_name": o.model_name,
            "object_id": o.object_id,
            "operation": o.operation,
            "payload": o.payload,
            "created_at": o.created_at.isoformat(),
        } for o in pending]

        try:
            r = requests.post(
                f"{self.server_url}/api/sync/push/",
                json={"operations": ops},
                headers={"X-API-Key": self.api_key},
                timeout=30,
            )
            r.raise_for_status()
            data = r.json()

            synced_ids = data.get("synced_ids", [])
            SyncOperation.objects.filter(id__in=synced_ids).update(synced_at=timezone.now())

            for op_id, err in data.get("errors", {}).items():
                SyncOperation.objects.filter(id=op_id).update(error_message=str(err))

            st = self._state(); st.is_online = True; st.last_sync_at = timezone.now(); st.save()
            return {"pushed": len(synced_ids), "failed": len(data.get("errors", {}))}
        except requests.RequestException as e:
            st = self._state(); st.is_online = False; st.save()
            return {"pushed": 0, "failed": len(ops), "error": str(e)}

    def pull_snapshot(self):
        st = self._state()
        try:
            r = requests.get(
                f"{self.server_url}/api/sync/snapshot/",
                params={"since": st.last_snapshot_version or ""},
                headers={"X-API-Key": self.api_key},
                timeout=60,
            )
            r.raise_for_status()
            snap = r.json()
            if snap.get("version") == st.last_snapshot_version:
                return {"updated": 0, "version": st.last_snapshot_version}

            applied = self._apply_snapshot(snap)
            st.last_snapshot_version = snap["version"]
            st.last_sync_at = timezone.now()
            st.is_online = True
            st.save()
            return {"updated": applied, "version": snap["version"]}
        except requests.RequestException as e:
            st.is_online = False; st.save()
            return {"updated": 0, "error": str(e)}

    def _apply_snapshot(self, snapshot):
        from django.apps import apps
        count = 0
        for model_name, records in snapshot.get("data", {}).items():
            app_label, cls = model_name.split(".")
            model = apps.get_model(app_label, cls)
            for rec in records:
                obj_id = rec.pop("id", None)
                if rec.get("_deleted"):
                    model.objects.filter(pk=obj_id).delete()
                else:
                    model.objects.update_or_create(pk=obj_id, defaults=rec)
                count += 1
        return count
