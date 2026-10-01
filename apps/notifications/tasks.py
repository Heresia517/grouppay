from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from .models import Notification

@shared_task
def send_email_notification(notification_id):
    """Envoie un email en arrière-plan."""
    try:
        notif = Notification.objects.get(id=notification_id)
        send_mail(
            subject=notif.title,
            message=notif.body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[notif.recipient.email],
            fail_silently=False,
        )
        notif.is_read = True
        notif.save()
    except Exception as e:
        print(f"Erreur envoi email : {e}")

@shared_task
def send_sms_notification(notification_id):
    """Envoie un SMS (stub pour la démo)."""
    try:
        notif = Notification.objects.get(id=notification_id)
        # TODO: intégrer Africa's Talking ou Orange Burkina API
        # Pour la démo, on logue juste
        print(f"SMS à {notif.recipient.internal_id}: {notif.body}")
    except Exception as e:
        print(f"Erreur envoi SMS : {e}")
