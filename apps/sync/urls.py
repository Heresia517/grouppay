from django.urls import path
from .api_views import SyncPushView, SyncSnapshotView

app_name = "sync"

urlpatterns = [
    path("push/", SyncPushView.as_view(), name="push"),
    path("snapshot/", SyncSnapshotView.as_view(), name="snapshot"),
]
