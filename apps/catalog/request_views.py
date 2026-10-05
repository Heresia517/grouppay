"""Vues wishlist collaborative (ProductRequest + votes)."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from .models import ProductRequest, ProductRequestVote


@login_required
def requests_list(request):
    """Liste des propositions (triées par votes)."""
    org = request.user.organization

    # Filtre statut
    status = request.GET.get("status", "OPEN")
    qs = ProductRequest.objects.filter(organization=org)

    if status and status != "ALL":
        qs = qs.filter(status=status)

    # Annoter le nombre de votes et si l'user a voté
    qs = qs.annotate(
        num_votes=Count("votes"),
        user_voted=Count("votes", filter=Q(votes__member=request.user)),
    ).order_by("-num_votes", "-created_at")

    # Mes propositions
    my_requests = ProductRequest.objects.filter(
        organization=org, proposed_by=request.user,
    ).annotate(num_votes=Count("votes")).order_by("-created_at")

    context = {
        "requests": qs,
        "my_requests": my_requests,
        "status_filter": status,
        "statuses": ProductRequest.STATUS_CHOICES,
        "stats": {
            "total": ProductRequest.objects.filter(organization=org).count(),
            "open": ProductRequest.objects.filter(organization=org, status="OPEN").count(),
            "reviewing": ProductRequest.objects.filter(organization=org, status="REVIEWING").count(),
            "accepted": ProductRequest.objects.filter(organization=org, status="ACCEPTED").count(),
        },
    }
    return render(request, "catalog/requests_list.html", context)


@login_required
def request_create(request):
    """Créer une nouvelle proposition."""
    if request.method == "POST":
        title = (request.POST.get("title") or "").strip()
        description = (request.POST.get("description") or "").strip()
        category_hint = (request.POST.get("category_hint") or "").strip()
        target_price = request.POST.get("target_price")

        if not title:
            messages.error(request, "Le titre est obligatoire.")
            return render(request, "catalog/request_form.html")

        try:
            target_price = float(target_price) if target_price else None
        except (TypeError, ValueError):
            target_price = None

        req = ProductRequest.objects.create(
            organization=request.user.organization,
            title=title,
            description=description,
            category_hint=category_hint,
            target_price=target_price,
            proposed_by=request.user,
            status="OPEN",
        )
        # L'auteur vote automatiquement pour sa proposition
        ProductRequestVote.objects.create(
            organization=request.user.organization,
            request=req, member=request.user,
        )

        messages.success(request, f"Proposition « {title} » créée !")
        return redirect("requests_list")

    return render(request, "catalog/request_form.html")


@login_required
@require_POST
def vote_request(request, request_id):
    """Voter ou retirer son vote."""
    req = get_object_or_404(
        ProductRequest, id=request_id, organization=request.user.organization,
    )

    if req.status in ("ARCHIVED", "REJECTED"):
        messages.error(request, "Cette proposition n'accepte plus de votes.")
        return redirect("requests_list")

    vote, created = ProductRequestVote.objects.get_or_create(
        organization=request.user.organization,
        request=req, member=request.user,
    )
    if not created:
        vote.delete()
        messages.info(request, "Vote retiré.")
    else:
        messages.success(request, "Vote enregistré !")

    return redirect("requests_list")


@login_required
@require_POST
def delete_request(request, request_id):
    """Supprimer sa propre proposition."""
    req = get_object_or_404(
        ProductRequest, id=request_id, organization=request.user.organization,
    )
    if req.proposed_by_id != request.user.id and request.user.role not in ("ADMIN", "GESTIONNAIRE"):
        raise PermissionDenied("Vous ne pouvez supprimer que vos propres propositions.")
    req.delete()
    messages.success(request, "Proposition supprimée.")
    return redirect("requests_list")


@login_required
@require_POST
def update_request_status(request, request_id):
    """RH : changer le statut d'une proposition."""
    if request.user.role not in ("ADMIN", "GESTIONNAIRE"):
        raise PermissionDenied("Réservé RH/Admin")

    req = get_object_or_404(
        ProductRequest, id=request_id, organization=request.user.organization,
    )
    new_status = request.POST.get("status")
    if new_status not in [c[0] for c in ProductRequest.STATUS_CHOICES]:
        messages.error(request, "Statut invalide.")
        return redirect("requests_list")

    req.status = new_status
    req.reviewed_by = request.user
    req.review_note = (request.POST.get("note") or "").strip()
    req.save(update_fields=["status", "reviewed_by", "review_note", "updated_at"])

    messages.success(request, f"Statut → {req.get_status_display()}")
    return redirect("requests_list")
