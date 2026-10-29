"""Vue post-login : dispatche l'utilisateur selon son role."""
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


@login_required
def post_login_redirect(request):
    """Redirige l'utilisateur vers son espace selon son role."""
    user = request.user

    # Si l'utilisateur venait d'une page specifique (next), respecter
    next_url = request.GET.get("next", "")
    if next_url and next_url.startswith("/"):
        return redirect(next_url)

    # Dispatch selon le role
    if user.is_superuser or user.role == "ADMIN" or getattr(user, "is_dg", False):
        return redirect("/admin/")  # Les admins vont directement sur Django Admin

    if user.role == "GESTIONNAIRE":
        return redirect("/rh/dashboard/")  # Les RH vont sur leur dashboard

    if user.role == "LIVREUR":
        return redirect("/deliveries/")  # Les livreurs voient leurs livraisons

    if user.role == "FOURNISSEUR":
        return redirect("/supplier/products/")  # Les fournisseurs voient leurs produits

    # Par defaut (membres, chefs, etc.)
    return redirect("/dashboard/")
