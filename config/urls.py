from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter

from apps.catalog.views import catalog, product_detail
from apps.catalog.supplier_views import supplier_dashboard
from apps.catalog.review_views import product_reviews, submit_review, delete_review
from apps.catalog.stock_views import (
    stock_dashboard, product_stock_history, adjust_stock, resolve_alert,
)
from apps.orders.views import (
    view_cart, add_to_cart, remove_from_cart, update_cart_item_qty,
    create_order_view, order_detail, my_orders,
    toggle_wishlist, wishlist_page, apply_coupon, remove_coupon,
)
from apps.documents.views import (
    download_purchase_order_pdf, preview_purchase_order_pdf, preview_order_html,
    preview_invoice_html, preview_invoice_pdf, download_invoice_pdf,
)
from apps.deliveries.views import courier_deliveries, delivery_detail, update_delivery_status
from apps.orders.dashboard_views import rh_dashboard, bulk_validate_orders, bulk_reject_orders
from apps.deductions.views import (
    deductions_dashboard, preview_export, generate_export, download_batch, mark_batch_sent,
)
from apps.orders.export_views import export_dashboard_excel, export_dashboard_pdf
from apps.accounts.views import (
    profile, save_theme, import_members_page, import_members_csv, import_members_template,
)
from apps.notifications.views import (
    unread_count, notification_list, mark_notification_read, mark_all_read,
)

from apps.catalog.viewsets import CategoryViewSet, ProductViewSet
from apps.orders.viewsets import CartViewSet, OrderViewSet

# DRF Router
router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'cart', CartViewSet, basename='cart')
router.register(r'orders', OrderViewSet, basename='order')

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path('admin/', admin.site.urls),
    
    # Catalogue
    path('', catalog, name='catalog'),
    path('product/<uuid:product_id>/', product_detail, name='product_detail'),
    
    # Panier
    path('cart/', view_cart, name='view_cart'),
    path('cart/add/<uuid:product_id>/', add_to_cart, name='add_to_cart'),
    path('cart/remove/<uuid:item_id>/', remove_from_cart, name='remove_from_cart'),
    path('cart/update/<uuid:item_id>/', update_cart_item_qty, name='update_cart_item_qty'),
    path('cart/apply-coupon/', apply_coupon, name='apply_coupon'),
    path('cart/remove-coupon/', remove_coupon, name='remove_coupon'),

    # Wishlist
    path('wishlist/', wishlist_page, name='wishlist'),
    path('wishlist/toggle/<uuid:product_id>/', toggle_wishlist, name='toggle_wishlist'),
    path('cart/checkout/', create_order_view, name='create_order'),
    
    # Commandes
    path('orders/my/', my_orders, name='my_orders'),
    path('orders/<uuid:order_id>/', order_detail, name='order_detail'),
    path('orders/<uuid:order_id>/pdf/', download_purchase_order_pdf, name='download_pdf'),
    path('orders/<uuid:order_id>/pdf/preview/', preview_purchase_order_pdf, name='preview_pdf'),
    path('orders/<uuid:order_id>/preview/', preview_order_html, name='preview_order_html'),
    path('orders/<uuid:order_id>/invoice/', preview_invoice_html, name='preview_invoice_html'),
    path('orders/<uuid:order_id>/invoice/pdf/', download_invoice_pdf, name='download_invoice_pdf'),
    path('orders/<uuid:order_id>/invoice/pdf/preview/', preview_invoice_pdf, name='preview_invoice_pdf'),
    path('orders/<uuid:order_id>/pdf/preview/', preview_purchase_order_pdf, name='preview_pdf'),
    
    # Livraisons
    path('deliveries/', courier_deliveries, name='courier_deliveries'),
    path('deliveries/<uuid:delivery_id>/', delivery_detail, name='delivery_detail'),
    path('deliveries/<uuid:delivery_id>/update/', update_delivery_status, name='update_delivery_status'),
    
    # API REST
    # Stock avancé
    path('stock/', stock_dashboard, name='stock_dashboard'),
    path('stock/product/<uuid:product_id>/', product_stock_history, name='stock_history'),
    path('stock/product/<uuid:product_id>/adjust/', adjust_stock, name='adjust_stock'),
    path('stock/alert/<uuid:alert_id>/resolve/', resolve_alert, name='resolve_alert'),

    # Avis produits
    path('product/<uuid:product_id>/reviews/', product_reviews, name='product_reviews'),
    path('product/<uuid:product_id>/review/', submit_review, name='submit_review'),
    path('review/<uuid:review_id>/delete/', delete_review, name='delete_review'),

    # Fournisseur
    path('supplier/', supplier_dashboard, name='supplier_dashboard'),

    # RH Dashboard
    path('rh/dashboard/', rh_dashboard, name='rh_dashboard'),
    path('rh/orders/bulk-validate/', bulk_validate_orders, name='bulk_validate'),
    path('rh/orders/bulk-reject/', bulk_reject_orders, name='bulk_reject'),
    path('rh/dashboard/export/', export_dashboard_excel, name='export_dashboard_excel'),
    path('rh/dashboard/export-pdf/', export_dashboard_pdf, name='export_dashboard_pdf'),

    # Retenue salariale
    path('rh/deductions/', deductions_dashboard, name='deductions_dashboard'),
    path('rh/deductions/preview/', preview_export, name='preview_export'),
    path('rh/deductions/generate/', generate_export, name='generate_export'),
    path('rh/deductions/batch/<uuid:batch_id>/download/', download_batch, name='download_batch'),
    path('rh/deductions/batch/<uuid:batch_id>/sent/', mark_batch_sent, name='mark_batch_sent'),

    # Import membres RH
    path('rh/members/import/', import_members_page, name='import_members'),
    path('rh/members/import/upload/', import_members_csv, name='import_members_upload'),
    path('rh/members/import/template/', import_members_template, name='import_members_template'),

    # Profil
    path('profile/', profile, name='profile'),
    path('api/theme/', save_theme, name='save_theme'),

    # Notifications
    path('api/notifications/unread-count/', unread_count, name='notif_unread_count'),
    path('api/notifications/list/', notification_list, name='notif_list'),
    path('api/notifications/<uuid:notif_id>/read/', mark_notification_read, name='notif_mark_read'),
    path('api/notifications/mark-all-read/', mark_all_read, name='notif_mark_all_read'),

    # API REST
    path('api/v1/', include(router.urls)),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
