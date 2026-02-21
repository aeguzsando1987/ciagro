from rest_framework.permissions import BasePermission


class IsGuest(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.user_role is not None
            and request.user.user_role.level >= 1
        )


class IsTechnician(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.user_role is not None
            and request.user.user_role.level >= 2
        )


class IsSupervisor(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.user_role is not None
            and request.user.user_role.level >= 3
        )


class IsGerente(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.user_role is not None
            and request.user.user_role.level >= 4
        )


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.user_role is not None
            and request.user.user_role.level >= 5
        )
        
        