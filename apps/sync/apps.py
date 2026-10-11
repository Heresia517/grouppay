from django.apps import AppConfig
from django.conf import settings


class SyncConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.sync"
    verbose_name = "Synchronisation hybride"

    def ready(self):
        # Charger les signaux de capture
        from . import signals  # noqa

        # En mode desktop + sync activée : lancer la boucle en arrière-plan
        if getattr(settings, "IS_DESKTOP", False) and getattr(settings, "SYNC_ENABLED", False):
            import threading
            from .services import SyncService

            def _loop():
                import time
                service = SyncService()
                # Délai initial pour laisser Django démarrer
                time.sleep(5)
                while True:
                    try:
                        service.push_pending()
                        service.pull_snapshot()
                    except Exception:
                        pass
                    time.sleep(120)

            t = threading.Thread(target=_loop, daemon=True, name="grouppay-sync")
            t.start()
