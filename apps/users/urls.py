# apps/users/urls.py
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from drf_spectacular.utils import extend_schema

from apps.users.views import (
    AdminRegisterView,
    PublicRegisterView,
    ChangePasswordView,
    LoginView,
    LogoutView,
    UserRoleListView,
    WorkRoleListView,
    UserListView,
    UserDestroyView,
    UserMeView,
    UserAssignmentListView,
    UserAssignmentCreateView,
    UserAssignmentDestroyView,
    )

# Taggear TokenRefreshView de simplejwt sin crear subclase
TokenRefreshView = extend_schema(
    tags=["auth"],
    summary="Refrescar access token",
    description=(
        "Recibe un `refresh` token valido y retorna un nuevo `access` token (y un nuevo `refresh` "
        "si `ROTATE_REFRESH_TOKENS=True`). El refresh anterior queda en la blacklist."
    ),
)(TokenRefreshView)

app_name = "users"

urlpatterns = [
    # Login: recibe username+password, retorna access+refresh tokens
    path("auth/login/", LoginView.as_view(), name="auth_login"),
    # Refresh: recibe refresh token, retorna nuevo access token
    path("auth/refresh/", TokenRefreshView.as_view(), name="auth_refresh"),
    # Logout: invalida el refresh token en la blacklist
    path("auth/logout/", LogoutView.as_view(), name="auth_logout"),
    # Cambio de password autenticado
    path("auth/change-password/", ChangePasswordView.as_view(), name="auth_change_password"),
    # Registro de usuario Admin
    path("auth/register/", AdminRegisterView.as_view(), name="auth_admin_register"),
    # Registro de usuario
    path("auth/signup/", PublicRegisterView.as_view(), name="auth_public_register"),
    # Listado de usuarios y roles
    path("users/", UserListView.as_view(), name="user_list"),
    path("users/me/", UserMeView.as_view(), name="user_me"),
    path("users/roles/", UserRoleListView.as_view(), name="user_role_list"),
    path("users/work-roles/", WorkRoleListView.as_view(), name="work_role_list"),
    path("users/<uuid:pk>/", UserDestroyView.as_view(), name="user_destroy"),
    # Asignaciones user ↔ agro_unit
    path("users/assignments/", UserAssignmentListView.as_view(), name="user_assignment_list"),
    path("users/assignments/create/", UserAssignmentCreateView.as_view(), name="user_assignment_create"),
    path("users/assignments/<int:pk>/delete/", UserAssignmentDestroyView.as_view(), name="user_assignment_destroy"),
]
