"""URLs orders — ZionPay."""
from django.urls import path
from apps.orders.views import order_bon_commande_pdf

app_name = "orders"

urlpatterns = [
    path("<uuid:order_id>/bon-commande.pdf", order_bon_commande_pdf, name="bon_commande_pdf"),
]
