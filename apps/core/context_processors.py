"""Context processors globaux."""
from .helpers import is_internal_staff, is_member


def grouppay_context(request):
    """Ajoute des variables globales a tous les templates."""
    user = request.user

    # Determine l'espace actuel depuis l'URL
    path = request.path or ""
    current_space = "mutuelle"  # par defaut
    if path.startswith("/da/") or path.startswith("/rh/") or path.startswith("/stock/"):
        current_space = "da"
    elif path.startswith("/inventory/"):
        current_space = "inventory"

    return {
        "is_internal_staff": is_internal_staff(user),
        "is_member_only": is_member(user),
        "current_space": current_space,
        "can_access_da": is_internal_staff(user),
    }
