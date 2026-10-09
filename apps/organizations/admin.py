from django.contrib import admin
from .models import Direction, Service, Organization

admin.site.register(Organization)


@admin.register(Direction)
class DirectionAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "organization", "director", "is_achats", "is_active")
    list_filter = ("organization", "is_achats", "is_active")
    search_fields = ("code", "name")
    list_editable = ("is_active",)


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "direction", "chief", "is_active")
    list_filter = ("organization", "direction", "is_active")
    search_fields = ("code", "name")
    list_editable = ("is_active",)



from .models import Currency, ExchangeRate


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "symbol", "is_active")
    list_filter = ("is_active",)


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ("from_currency", "to_currency", "rate", "source", "fetched_at")
    list_filter = ("from_currency", "to_currency")
