"""Calculs fiscaux et sociaux Burkina Faso."""
from decimal import Decimal, ROUND_HALF_UP
from django.core.exceptions import ValidationError


def arrondi_fcfa(montant):
    """Arrondit au FCFA entier (pas de centimes en XOF)."""
    if montant is None:
        return 0
    return int(Decimal(str(montant)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def calcul_tva(montant_ht, taux=Decimal("0.18")):
    """Calcule TVA BF (18% par défaut). Retourne (ht, tva, ttc)."""
    ht = Decimal(str(montant_ht))
    tva = (ht * Decimal(str(taux))).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    ttc = (ht + tva).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return int(ht), int(tva), int(ttc)


def calcul_iuts(salaire_brut_mensuel, annee=2024):
    """Calcule l'IUTS selon le barème progressif BF.

    Retourne un dict avec le détail par tranche.
    """
    from .models import BaremeIUTS
    brut = Decimal(str(salaire_brut_mensuel))
    baremes = BaremeIUTS.objects.filter(actif=True, annee=annee).order_by("ordre", "tranche_min")
    if not baremes.exists():
        return {"iuts_total": 0, "tranches": [], "erreur": "Aucun barème configuré"}

    iuts_total = Decimal("0")
    tranches_detail = []
    for b in baremes:
        if brut <= Decimal(str(b.tranche_min)):
            break
        max_val = Decimal(str(b.tranche_max)) if b.tranche_max else brut
        base = min(brut, max_val) - Decimal(str(b.tranche_min))
        if base <= 0:
            continue
        impot = (base * b.taux).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        iuts_total += impot
        tranches_detail.append({
            "tranche": f"{b.tranche_min:,} – {b.tranche_max:,}" if b.tranche_max else f">{b.tranche_min:,}",
            "base": int(base),
            "taux": float(b.taux),
            "impot": int(impot),
        })

    return {
        "iuts_total": int(iuts_total),
        "salaire_brut": int(brut),
        "salaire_net_avant_cnss": int(brut - iuts_total),
        "tranches": tranches_detail,
    }


def calcul_cnss(salaire_brut_mensuel, annee=2024):
    """Calcule les cotisations CNSS employeur et salarié."""
    from .models import TauxCNSS, ParametreFiscalBF
    brut = Decimal(str(salaire_brut_mensuel))
    param = ParametreFiscalBF.objects.filter(annee=annee, actif=True).first()
    plafond = Decimal(str(param.plafond_cnss)) if param else Decimal("600000")
    base = min(brut, plafond)

    taux = TauxCNSS.objects.filter(actif=True, annee=annee)
    cnss_salarie = sum((base * t.taux for t in taux if t.part == "salarie"), Decimal("0"))
    cnss_employeur = sum((base * t.taux for t in taux if t.part == "employeur"), Decimal("0"))

    return {
        "base_cotisable": int(base),
        "plafond": int(plafond),
        "salarie": int(cnss_salarie.quantize(Decimal("1"), rounding=ROUND_HALF_UP)),
        "employeur": int(cnss_employeur.quantize(Decimal("1"), rounding=ROUND_HALF_UP)),
        "total": int((cnss_salarie + cnss_employeur).quantize(Decimal("1"), rounding=ROUND_HALF_UP)),
    }


def fiche_paie_burkina(salaire_brut, annee=2024):
    """Calcule une fiche de paie complète BF.

    Retourne brut, IUTS, CNSS salarié, net à payer, coût employeur.
    """
    iuts = calcul_iuts(salaire_brut, annee)
    cnss = calcul_cnss(salaire_brut, annee)
    net = iuts["salaire_brut"] - iuts["iuts_total"] - cnss["salarie"]
    cout_employeur = iuts["salaire_brut"] + cnss["employeur"]

    return {
        "salaire_brut": int(salaire_brut),
        "iuts": iuts["iuts_total"],
        "cnss_salarie": cnss["salarie"],
        "cnss_employeur": cnss["employeur"],
        "salaire_net": net,
        "cout_total_employeur": cout_employeur,
        "detail_iuts": iuts["tranches"],
        "detail_cnss": cnss,
    }
