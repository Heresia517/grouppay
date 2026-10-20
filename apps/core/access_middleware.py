"""Middleware de controle d'acces par espace."""
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

from .helpers import is_internal_staff, is_inventory_manager


# Paths protegees et roles autorises
PROTECTED_PATHS = {
    "/da/": "internal",         # DA : personnel interne uniquement
    "/inventory/": "inventory",  # Inventaire : gestionnaires uniquement
    "/stock/": "stock",      # Stock : personnel interne uniquement
    "/rh/": "rh",               # RH : RH/ADMIN uniquement
    "/supplier/": "supplier",   # Espace fournisseur : fournisseurs ou admin
    "/deliveries/": "courier",  # Livraisons : livreur ou admin
}

# Exceptions (URLs publiques dans ces paths)
PUBLIC_EXCEPTIONS = [
    "/da/verify/",     # Verification signature publique
]


class AccessControlMiddleware:
    """Verifie que l'utilisateur a le droit d'acceder au path demande."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        # Passer les paths publics
        for exception_path in PUBLIC_EXCEPTIONS:
            if path.startswith(exception_path):
                return self.get_response(request)

        # Determiner le type de protection
        required = None
        for prefix, role in PROTECTED_PATHS.items():
            if path.startswith(prefix):
                required = role
                break

        if required is None:
            # Path non protege
            return self.get_response(request)

        # Auth obligatoire pour tous les paths proteges
        if not request.user.is_authenticated:
            return redirect(f"{settings.LOGIN_URL}?next={path}")

        # Verifier selon le type
        if required == "internal":
            if not is_internal_staff(request.user):
                raise PermissionDenied(
                    "Acces reserve au personnel interne (chef, directeur, DG, RH, achats)."
                )

        elif required == "inventory":
            if not is_inventory_manager(request.user):
                raise PermissionDenied(
                    "Acces reserve aux gestionnaires d'inventaire (RH, Admin, Achats)."
                )

        elif required == "rh":
            if request.user.role not in ("ADMIN", "GESTIONNAIRE") and not request.user.is_dg:
                raise PermissionDenied("Acces reserve aux RH et administrateurs.")

        elif required == "supplier":
            if request.user.role not in ("FOURNISSEUR", "ADMIN") and not request.user.is_dg:
                raise PermissionDenied("Acces reserve aux fournisseurs.")

        elif required == "stock":
            if request.user.role not in ("FOURNISSEUR", "ADMIN", "GESTIONNAIRE") and not request.user.is_dg:
                raise PermissionDenied("Acces reserve aux fournisseurs, gestionnaires et administrateurs.")

        elif required == "courier":
            if request.user.role not in ("LIVREUR", "ADMIN") and not request.user.is_dg:
                raise PermissionDenied("Acces reserve aux livreurs.")

        return self.get_response(request)
