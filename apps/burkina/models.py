"""Barèmes fiscaux et sociaux du Burkina Faso."""
from django.db import models


class BaremeIUTS(models.Model):
    """Barème IUTS (Impôt Unique sur les Traitements et Salaires) Burkina Faso.

    Barème progressif par tranches mensuelles, en FCFA.
    Source : CGI Burkina Faso 2024.
    """
    tranche_min = models.BigIntegerField(help_text="Borne inférieure mensuelle (FCFA)")
    tranche_max = models.BigIntegerField(null=True, blank=True,
                                          help_text="Borne supérieure (null = dernier)")
    taux = models.DecimalField(max_digits=5, decimal_places=4,
                                help_text="Taux appliqué à la tranche (ex: 0.1210 = 12,10%)")
    ordre = models.PositiveIntegerField(default=0, help_text="Ordre d'application")
    actif = models.BooleanField(default=True)
    annee = models.PositiveIntegerField(default=2024)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["ordre", "tranche_min"]
        verbose_name = "Barème IUTS"
        verbose_name_plural = "Barèmes IUTS"

    def __str__(self):
        max_txt = f"{self.tranche_max:,}" if self.tranche_max else "∞"
        return f"[{self.tranche_min:,} – {max_txt}] {float(self.taux)*100:.2f}%"


class TauxCNSS(models.Model):
    """Taux de cotisation CNSS Burkina Faso.

    - Employeur : 16% (prestations familiales 6%, vieillesse 5,5%, risques pro 4%, etc.)
    - Salarié : 5,5% (vieillesse uniquement)
    """
    CODES = [
        ("PF", "Prestations familiales"),
        ("VIEILLESSE", "Assurance vieillesse"),
        ("RP", "Risques professionnels"),
        ("ECLAIR", "Œuvres sociales / éclairage"),
    ]
    code = models.CharField(max_length=20, choices=CODES)
    libelle = models.CharField(max_length=100)
    taux = models.DecimalField(max_digits=5, decimal_places=4)
    part = models.CharField(max_length=10, choices=[("employeur", "Employeur"), ("salarie", "Salarié")])
    actif = models.BooleanField(default=True)
    annee = models.PositiveIntegerField(default=2024)

    class Meta:
        unique_together = [("code", "part", "annee")]
        verbose_name = "Taux CNSS"
        verbose_name_plural = "Taux CNSS"

    def __str__(self):
        return f"{self.libelle} ({self.part}) : {float(self.taux)*100:.2f}%"


class ParametreFiscalBF(models.Model):
    """Paramètres fiscaux annuels (TVA, SMIG, plafonds, etc.)."""
    annee = models.PositiveIntegerField()
    tva_standard = models.DecimalField(max_digits=5, decimal_places=4, default=0.18)
    smig_mensuel = models.BigIntegerField(default=45000, help_text="SMIG mensuel FCFA")
    plafond_cnss = models.BigIntegerField(default=600000, help_text="Plafond cotisable CNSS FCFA")
    taux_iuts_max = models.DecimalField(max_digits=5, decimal_places=4, default=0.2510)
    devise = models.CharField(max_length=3, default="XOF")
    actif = models.BooleanField(default=True)

    class Meta:
        ordering = ["-annee"]
        verbose_name = "Paramètre fiscal BF"

    def __str__(self):
        return f"BF {self.annee} (TVA {float(self.tva_standard)*100:.0f}%)"
