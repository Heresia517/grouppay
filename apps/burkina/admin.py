from django.contrib import admin
from .models import BaremeIUTS, TauxCNSS, ParametreFiscalBF


@admin.register(BaremeIUTS)
class BaremeIUTSAdmin(admin.ModelAdmin):
    list_display = ("__str__", "taux", "ordre", "annee", "actif")
    list_filter = ("annee", "actif")
    ordering = ("ordre", "tranche_min")


@admin.register(TauxCNSS)
class TauxCNSSAdmin(admin.ModelAdmin):
    list_display = ("code", "libelle", "part", "taux", "annee", "actif")
    list_filter = ("part", "annee", "actif")


@admin.register(ParametreFiscalBF)
class ParametreFiscalBFAdmin(admin.ModelAdmin):
    list_display = ("annee", "tva_standard", "smig_mensuel", "plafond_cnss", "actif")
    list_filter = ("annee", "actif")
