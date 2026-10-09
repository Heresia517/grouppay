from django.urls import path
from . import views


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
]
