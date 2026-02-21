# apps/users/views.py
from django.contrib.auth import update_session_auth_hash
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.users.serializers import CIAgroTokenObtainPairSerializer


class LoginView(TokenObtainPairView):
    """
    POST /api/v1/auth/login/
    Recibe: { "username": "...", "password": "..." }
    Retorna: { "access": "...", "refresh": "..." }
    El access token incluye claims de rol (role_name, role_level).
    """
    serializer_class = CIAgroTokenObtainPairSerializer


class LogoutView(APIView):
    """
    POST /api/v1/auth/logout/
    Recibe: { "refresh": "<refresh_token>" }
    Invalida el refresh token en la blacklist.
    Sin esto, el logout es solo client-side (borrar el token del navegador).
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception:
            return Response(
                {"detail": "Token invalido o ya expirado."},
                status=status.HTTP_400_BAD_REQUEST,
            )


class ChangePasswordView(APIView):
    """
    POST /api/v1/auth/change-password/
    Recibe: { "old_password": "...", "new_password": "..." }
    Valida la contrasena actual antes de permitir el cambio.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        old_password = request.data.get("old_password")
        new_password = request.data.get("new_password")

        if not old_password or not new_password:
            return Response(
                {"detail": "Se requieren old_password y new_password."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not user.check_password(old_password):
            return Response(
                {"detail": "Contrasena actual incorrecta."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save()
        update_session_auth_hash(request, user)
        return Response(
            {"detail": "Contrasena actualizada correctamente."},
            status=status.HTTP_200_OK,
        )
