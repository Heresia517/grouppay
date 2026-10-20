"""Helpers globaux GroupPay."""


def is_internal_staff(user):
    """Verifie si l'utilisateur fait partie du personnel interne (a acces a la DA).

    Retourne True pour :
    - ADMIN
    - GESTIONNAIRE (RH)
    - Chef de service (is_service_chief)
    - Directeur de direction (is_director)
    - DG (is_dg)
    - Membre d'une direction des achats
    """
    if not user or not user.is_authenticated:
        return False

    # Roles admin/RH
    if user.role in ("ADMIN", "GESTIONNAIRE"):
        return True

    # Roles organisationnels
    if getattr(user, "is_dg", False):
        return True
    if getattr(user, "is_director", False):
        return True
    if getattr(user, "is_service_chief", False):
        return True

    # Membre de la direction des achats
    if user.service and user.service.direction and user.service.direction.is_achats:
        return True

    return False


def is_member(user):
    """Verifie si l'utilisateur est un membre simple (acces Mutuelle seulement)."""
    if not user or not user.is_authenticated:
        return False
    return not is_internal_staff(user)



def is_inventory_manager(user):
    """Verifie si l'utilisateur peut gerer l'inventaire.

    Autonomes :
    - ADMIN
    - DG
    - Membre de la direction des achats

    RH (GESTIONNAIRE) a aussi acces.
    """
    if not user or not user.is_authenticated:
        return False

    if user.role == "ADMIN":
        return True
    if getattr(user, "is_dg", False):
        return True
    if user.role == "GESTIONNAIRE":
        return True
    if user.service and user.service.direction and user.service.direction.is_achats:
        return True
    return False


def format_fcfa(montant):
    """Formate un montant en FCFA avec separateur espace."""
    if montant is None:
        return "0 FCFA"
    try:
        v = int(float(montant))
        return f"{v:,}".replace(",", " ") + " FCFA"
    except (ValueError, TypeError):
        return f"{montant} FCFA"
