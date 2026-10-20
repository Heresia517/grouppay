from django.apps import AppConfig


class DeliveriesConfig(AppConfig):
    name = 'apps.deliveries'

    def ready(self):
        import apps.deliveries.signals  # noqa
