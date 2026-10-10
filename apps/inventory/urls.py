from django.urls import path
from . import views


urlpatterns = [
    path("", views.inventory_dashboard, name="inventory_dashboard"),
    path("assets/", views.asset_list, name="asset_list"),
    path("assets/new/", views.asset_form, name="asset_create"),
    path("assets/<uuid:asset_id>/", views.asset_detail, name="asset_detail"),
    path("assets/<uuid:asset_id>/edit/", views.asset_form, name="asset_edit"),
    path("assets/<uuid:asset_id>/assign/", views.asset_assign, name="asset_assign"),
    path("assets/<uuid:asset_id>/return/", views.asset_return, name="asset_return"),
    path("assets/<uuid:asset_id>/maintenance/", views.maintenance_form, name="asset_maintenance"),
    path("assets/<uuid:asset_id>/status/", views.asset_change_status, name="asset_change_status"),
]
