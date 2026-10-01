from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter

from apps.catalog.views import catalog, product_detail
from apps.orders.views import view_cart, add_to_cart, remove_from_cart, create_order_view, order_detail, my_orders
from apps.documents.views import download_purchase_order_pdf
from apps.deliveries.views import courier_deliveries, delivery_detail, update_delivery_status

from apps.catalog.viewsets import CategoryViewSet, ProductViewSet
from apps.orders.viewsets import CartViewSet, OrderViewSet

# DRF Router
router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'cart', CartViewSet, basename='cart')
router.register(r'orders', OrderViewSet, basename='order')

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Catalogue
    path('', catalog, name='catalog'),
    path('product/<uuid:product_id>/', product_detail, name='product_detail'),
    
    # Panier
    path('cart/', view_cart, name='view_cart'),
    path('cart/add/<uuid:product_id>/', add_to_cart, name='add_to_cart'),
    path('cart/remove/<uuid:item_id>/', remove_from_cart, name='remove_from_cart'),
    path('cart/checkout/', create_order_view, name='create_order'),
    
    # Commandes
    path('orders/my/', my_orders, name='my_orders'),
    path('orders/<uuid:order_id>/', order_detail, name='order_detail'),
    path('orders/<uuid:order_id>/pdf/', download_purchase_order_pdf, name='download_pdf'),
    
    # Livraisons
    path('deliveries/', courier_deliveries, name='courier_deliveries'),
    path('deliveries/<uuid:delivery_id>/', delivery_detail, name='delivery_detail'),
    path('deliveries/<uuid:delivery_id>/update/', update_delivery_status, name='update_delivery_status'),
    
    # API REST
    path('api/v1/', include(router.urls)),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
