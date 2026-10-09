from django.urls import path
from . import views
from . import admin_views


urlpatterns = [
    # Dashboard & listes
    path("", views.da_dashboard, name="da_dashboard"),
    path("requests/", views.da_list, name="da_list"),
    path("items/", views.da_items_catalog, name="da_items_catalog"),

    # Creation & detail
    path("requests/new/", views.da_create, name="da_create"),
    path("requests/<uuid:request_id>/", views.da_detail, name="da_detail"),

    # Actions workflow
    path("requests/<uuid:request_id>/submit/", views.da_submit, name="da_submit"),
    path("requests/<uuid:request_id>/visa/", views.da_visa, name="da_visa"),
    path("requests/<uuid:request_id>/verify-stock/", views.da_verify_stock, name="da_verify_stock"),
    path("requests/<uuid:request_id>/order/", views.da_order, name="da_order"),
    path("requests/<uuid:request_id>/receive/", views.da_receive_page, name="da_receive_page"),
    path("requests/<uuid:request_id>/receive/confirm/", views.da_receive, name="da_receive"),
    path("requests/<uuid:request_id>/close/", views.da_close_page, name="da_close_page"),
    path("requests/<uuid:request_id>/close/confirm/", views.da_close, name="da_close"),

    # Signature (2 etapes)
    path("requests/<uuid:request_id>/sign/", views.da_sign_page, name="da_sign_page"),
    path("requests/<uuid:request_id>/sign/verify/", views.da_sign_verify, name="da_sign_verify"),
    path("requests/<uuid:request_id>/sign/refuse/", views.da_sign_refuse, name="da_sign_refuse"),

    # PDF
    path("requests/<uuid:request_id>/pdf/", views.da_download_pdf, name="da_download_pdf"),
    path("requests/<uuid:request_id>/pdf/preview/", views.da_preview_pdf, name="da_preview_pdf"),

    # Verification publique
    path("verify/<str:signature_hash>/", views.verify_signature_public, name="da_verify_public"),

    # ═══════════════════════════════════════════════════════════════
    # ADMIN DA UI
    # ═══════════════════════════════════════════════════════════════
    path("admin/", admin_views.admin_home, name="da_admin_home"),

    # Categories
    path("admin/categories/", admin_views.admin_categories, name="da_admin_categories"),
    path("admin/categories/new/", admin_views.admin_category_form, name="da_admin_category_new"),
    path("admin/categories/<uuid:category_id>/edit/", admin_views.admin_category_form, name="da_admin_category_edit"),
    path("admin/categories/<uuid:category_id>/delete/", admin_views.admin_category_delete, name="da_admin_category_delete"),

    # Articles
    path("admin/items/", admin_views.admin_items, name="da_admin_items"),
    path("admin/items/new/", admin_views.admin_item_form, name="da_admin_item_new"),
    path("admin/items/<uuid:item_id>/edit/", admin_views.admin_item_form, name="da_admin_item_edit"),
    path("admin/items/<uuid:item_id>/delete/", admin_views.admin_item_delete, name="da_admin_item_delete"),
    path("admin/items/<uuid:item_id>/toggle/", admin_views.admin_item_toggle, name="da_admin_item_toggle"),
    path("admin/items/<uuid:item_id>/stock-adjust/", admin_views.admin_item_stock_adjust, name="da_admin_item_stock_adjust"),

    # Import CSV
    path("admin/items/import/", admin_views.admin_items_import, name="da_admin_items_import"),
    path("admin/items/import/upload/", admin_views.admin_items_import_upload, name="da_admin_items_import_upload"),
    path("admin/items/import/template/", admin_views.admin_items_import_template, name="da_admin_items_import_template"),

    # Directions
    path("admin/directions/", admin_views.admin_directions, name="da_admin_directions"),
    path("admin/directions/new/", admin_views.admin_direction_form, name="da_admin_direction_new"),
    path("admin/directions/<uuid:direction_id>/edit/", admin_views.admin_direction_form, name="da_admin_direction_edit"),
    path("admin/directions/<uuid:direction_id>/delete/", admin_views.admin_direction_delete, name="da_admin_direction_delete"),

    # Services
    path("admin/services/", admin_views.admin_services, name="da_admin_services"),
    path("admin/services/new/", admin_views.admin_service_form, name="da_admin_service_new"),
    path("admin/services/<uuid:service_id>/edit/", admin_views.admin_service_form, name="da_admin_service_edit"),
    path("admin/services/<uuid:service_id>/delete/", admin_views.admin_service_delete, name="da_admin_service_delete"),
]