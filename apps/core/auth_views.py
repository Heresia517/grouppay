"""Vues auth personnalisees."""
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

from .helpers import is_internal_staff


@login_required
def post_login_redirect(request):
    """Redirige l'utilisateur vers son dashboard unifie."""
    return redirect("dashboard")
