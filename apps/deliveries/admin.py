from django.contrib import admin
from .models import Delivery, DeliveryNoteDocument

admin.site.register(Delivery)
admin.site.register(DeliveryNoteDocument)