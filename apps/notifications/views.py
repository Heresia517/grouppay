"""Vues notifications — tolerant aux anonymes."""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from .models import Notification


def unread_count(request):
    """Retourne le nombre de notifications non lues.

    Si user non authentifie : retourne 0 (pas de 302/403).
    """
    if not request.user.is_authenticated:
        return JsonResponse({"count": 0})

    try:
        count = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).count()
    except Exception:
        count = 0
    return JsonResponse({"count": count})


def notification_list(request):
    """Liste des dernieres notifications."""
    if not request.user.is_authenticated:
        return JsonResponse({"notifications": []})

    try:
        notifs = Notification.objects.filter(
            recipient=request.user
        ).order_by("-created_at")[:10]
        data = [
            {
                "id": str(n.id),
                "title": n.title or "",
                "body": (n.body or "")[:100],
                "is_read": n.is_read,
                "created_at": n.created_at.strftime("%d/%m %H:%M"),
                "action_url": getattr(n, "action_url", "") or "",
            }
            for n in notifs
        ]
    except Exception:
        data = []
    return JsonResponse({"notifications": data})


@login_required
@require_POST
def mark_notification_read(request, notif_id):
    try:
        notif = Notification.objects.get(id=notif_id, recipient=request.user)
        notif.is_read = True
        notif.save(update_fields=["is_read"])
        return JsonResponse({"ok": True})
    except Notification.DoesNotExist:
        return JsonResponse({"ok": False, "error": "not_found"}, status=404)
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


@login_required
@require_POST
def mark_all_read(request):
    try:
        updated = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).update(is_read=True)
        return JsonResponse({"ok": True, "updated": updated})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)



@login_required
def notifications_page(request):
    """Page dediee a la liste des notifications."""
    from django.shortcuts import render
    notifs = Notification.objects.filter(
        recipient=request.user,
    ).order_by("-created_at")[:100]
    unread = Notification.objects.filter(recipient=request.user, is_read=False).count()

    return render(request, "notifications/list.html", {
        "notifications": notifs,
        "unread_count": unread,
    })
