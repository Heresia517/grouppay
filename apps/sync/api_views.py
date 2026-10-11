from django.conf import settings
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


def _check_key(request):
    key = request.headers.get("X-API-Key", "")
    return bool(settings.SYNC_API_KEY) and key == settings.SYNC_API_KEY


class SyncPushView(APIView):
    """Reçoit les opérations des clients (mode desktop)."""

    def post(self, request):
        if not _check_key(request):
            return Response({"error": "unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)

        from django.apps import apps
        ops = request.data.get("operations", [])
        synced, errors = [], {}

        for op in ops:
            try:
                app_label, cls = op["model_name"].split(".")
                model = apps.get_model(app_label, cls)
                if op["operation"] == "delete":
                    model.objects.filter(pk=op["object_id"]).delete()
                else:
                    model.objects.update_or_create(pk=op["object_id"], defaults=op["payload"])
                synced.append(op["id"])
            except Exception as e:
                errors[op["id"]] = str(e)

        return Response({
            "synced_ids": synced,
            "errors": errors,
            "server_version": timezone.now().isoformat(),
        })


class SyncSnapshotView(APIView):
    """Renvoie un snapshot des données au client."""

    def get(self, request):
        if not _check_key(request):
            return Response({"error": "unauthorized"}, status=status.HTTP_401_UNAUTHORIZED)

        # Exemple minimaliste — à adapter à vos modèles
        return Response({
            "version": timezone.now().isoformat(),
            "data": {},
        })
