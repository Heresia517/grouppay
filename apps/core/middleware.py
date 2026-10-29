"""ZionPay — Middleware métier."""
from django.http import HttpResponseForbidden


class OrganizationActiveMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if getattr(request, "user", None) and request.user.is_authenticated:
            org = getattr(request, "organization", None) or getattr(request.user, "organization", None)
            if org is not None and getattr(org, "is_suspended", False):
                return HttpResponseForbidden("Organisation suspendue. Contactez le support ZionPay.")
        return self.get_response(request)
