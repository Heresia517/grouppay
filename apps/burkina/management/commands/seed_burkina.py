"""Seed des barèmes fiscaux et sociaux Burkina Faso 2024."""
from decimal import Decimal
from django.core.management.base import BaseCommand
from apps.burkina.models import BaremeIUTS, TauxCNSS, ParametreFiscalBF


class Command(BaseCommand):
    help = "Initialise les barèmes IUTS/CNSS/TVA Burkina Faso 2024"

    def handle(self, *args, **options):
        annee = 2024

        # ─── Barème IUTS 2024 (mensuel, FCFA) ───
        # Source : CGI Burkina Faso — tranches progressives
        iuts = [
            (0, 50000, Decimal("0.0000"), 1),        # 0 à 50 000 : 0%
            (50000, 100000, Decimal("0.1210"), 2),   # 50 001 à 100 000 : 12,10%
            (100000, 200000, Decimal("0.1350"), 3),  # 100 001 à 200 000 : 13,50%
            (200000, 300000, Decimal("0.1550"), 4),  # 200 001 à 300 000 : 15,50%
            (300000, 500000, Decimal("0.1820"), 5),  # 300 001 à 500 000 : 18,20%
            (500000, None, Decimal("0.2510"), 6),    # > 500 000 : 25,10%
        ]
        for tmin, tmax, taux, ordre in iuts:
            BaremeIUTS.objects.update_or_create(
                tranche_min=tmin, annee=annee,
                defaults={"tranche_max": tmax, "taux": taux, "ordre": ordre, "actif": True}
            )
        self.stdout.write(self.style.SUCCESS(f"✓ {len(iuts)} tranches IUTS créées"))

        # ─── Taux CNSS 2024 ───
        cnss = [
            ("PF", "Prestations familiales", Decimal("0.0600"), "employeur"),
            ("VIEILLESSE", "Assurance vieillesse", Decimal("0.0550"), "employeur"),
            ("VIEILLESSE", "Assurance vieillesse", Decimal("0.0550"), "salarie"),
            ("RP", "Risques professionnels", Decimal("0.0400"), "employeur"),
            ("ECLAIR", "Œuvres sociales", Decimal("0.0050"), "employeur"),
        ]
        for code, lib, taux, part in cnss:
            TauxCNSS.objects.update_or_create(
                code=code, part=part, annee=annee,
                defaults={"libelle": lib, "taux": taux, "actif": True}
            )
        self.stdout.write(self.style.SUCCESS(f"✓ {len(cnss)} taux CNSS créés"))

        # ─── Paramètres fiscaux BF ───
        ParametreFiscalBF.objects.update_or_create(
            annee=annee,
            defaults={
                "tva_standard": Decimal("0.1800"),
                "smig_mensuel": 45000,
                "plafond_cnss": 600000,
                "taux_iuts_max": Decimal("0.2510"),
                "devise": "FCFA",
                "actif": True,
            }
        )
        self.stdout.write(self.style.SUCCESS("✓ Paramètres fiscaux BF 2024 créés"))
        self.stdout.write(self.style.SUCCESS("\n🎯 Burkina Faso prêt — TVA 18%, IUTS progressif, CNSS 16%+5,5%"))
