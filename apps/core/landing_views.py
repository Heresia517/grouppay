"""Vue landing page."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from .helpers import is_internal_staff


def landing(request):
    """Page d'accueil avec choix d'espace."""
    # Si non connecte -> landing publique
    if not request.user.is_authenticated:
        return render(request, "landing.html", {
            "is_public": True,
        })

    # Membre simple -> redirect direct vers le catalogue
    if not is_internal_staff(request.user):
        return redirect("catalog")

    # Staff -> afficher le choix
    return render(request, "landing.html", {
        "is_public": False,
        "is_internal": True,
    })
