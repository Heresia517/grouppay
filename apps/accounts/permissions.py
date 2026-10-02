from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "ADMIN")


class IsRH(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role in ("ADMIN", "GESTIONNAIRE"))


class IsRHOrAdmin(IsRH):
    pass


class IsCourier(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "LIVREUR")


class IsMember(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "MEMBRE")


class SameOrganization(BasePermission):
    """RG-05 : isolation multi-tenant."""
    def has_object_permission(self, request, view, obj):
        return getattr(obj, "organization_id", None) == request.user.organization_id
