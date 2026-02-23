# apps/users/urls.py
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from apps.users.views import AdminRegisterView, PublicRegisterView ,ChangePasswordView, LoginView, LogoutView

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
]
