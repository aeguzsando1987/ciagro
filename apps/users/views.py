# apps/users/views.py
from django.contrib.auth import update_session_auth_hash
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.users.models import Individual, User, UserRole, WorkRole, UserAssignment
from apps.users.serializers import (
    AdminRegisterSerializer,
    PublicRegisterSerializer,
    CIAgroTokenObtainPairSerializer,
    UserRoleSerializer,
    WorkRoleSerializer,
    IndividualSerializer,
    UserDetailSerializer,
    UserAssignmentSerializer,
)
from apps.users.permissions import IsSuperAdmin
from apps.core.mixins import SoftDeleteMixin




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
        user.requires_password_change = False
        user.save()
        update_session_auth_hash(request, user)
        return Response(
            {"detail": "Contrasena actualizada correctamente."},
            status=status.HTTP_200_OK,
        )


class AdminRegisterView(APIView):
    permission_classes = [IsSuperAdmin]

    def post(self, request):
        serializer = AdminRegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(
                {"detail": "Usuario creado exitosamente.", "username": user.username},
                status=status.HTTP_201_CREATED,
            )
        return Response(
            serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )
        
class PublicRegisterView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = PublicRegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(
                {"detail": "Usuario creado exitosamente.", "username": user.username},
                status=status.HTTP_201_CREATED,
            )
        return Response(
            serializer.errors, status=status.HTTP_400_BAD_REQUEST
        )
        
        
class UserRoleListView(generics.ListAPIView):
    """
    GET /api/v1/users/roles/
    Lista todos los roles de acceso. Usado para poblar dropdowns en el frontend.
    """
    permission_classes = [permissions.IsAuthenticated]
    queryset = UserRole.objects.all().order_by("level")
    serializer_class = UserRoleSerializer
    
    
class WorkRoleListView(generics.ListAPIView):
    """
    GET /api/v1/users/work-roles/
    Lista todos los roles laborales disponibles.
    """
    permission_classes = [permissions.IsAuthenticated]
    queryset = WorkRole.objects.all().order_by("work_name")
    serializer_class = WorkRoleSerializer
    

class UserListView(generics.ListAPIView):
    """
    GET /api/v1/users/
    Lista todos los usuarios activos. Solo SuperAdmin.
    """
    permission_classes = [IsSuperAdmin]
    queryset = User.objects.filter(is_deleted=False).select_related("user_role", "individual").order_by("username")
    serializer_class = UserDetailSerializer


class UserDestroyView(SoftDeleteMixin, generics.DestroyAPIView):
    """
    DELETE /api/v1/users/<uuid:pk>/
    Soft delete de usuario. Solo SuperAdmin.
    Marca is_deleted=True, registra deleted_at y deleted_by.
    No elimina el registro de la BD.
    """
    permission_classes = [IsSuperAdmin]
    queryset = User.objects.filter(is_deleted=False)
    
    
class UserAssignmentListView(generics.ListAPIView):
    """
    GET /api/v1/users/assignments/
    Lista asignaciones. Filtros opcionales: ?user=<uuid> y ?agro_unit=<uuid>.
    Solo SuperAdmin.
    """
    permission_classes = [IsSuperAdmin]
    serializer_class = UserAssignmentSerializer

    def get_queryset(self):
        qs = UserAssignment.objects.select_related("user", "agro_unit").order_by("agro_unit")
        user_id = self.request.query_params.get("user")
        agro_unit_id = self.request.query_params.get("agro_unit")
        if user_id:
            qs = qs.filter(user_id=user_id)
        if agro_unit_id:
            qs = qs.filter(agro_unit_id=agro_unit_id)
        return qs


class UserAssignmentCreateView(generics.CreateAPIView):
    """
    POST /api/v1/users/assignments/create/
    Crea una asignación user↔agro_unit.
    Solo SuperAdmin.
    """
    permission_classes = [IsSuperAdmin]
    queryset = UserAssignment.objects.all()
    serializer_class = UserAssignmentSerializer


class UserAssignmentDestroyView(generics.DestroyAPIView):
    """
    DELETE /api/v1/users/assignments/<int:pk>/delete/
    Elimina una asignación (hard delete — no hay datos de negocio en esta tabla pivote).
    Solo SuperAdmin.
    """
    permission_classes = [IsSuperAdmin]
    queryset = UserAssignment.objects.all()


class UserMeView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/v1/users/me/ — Perfil del usuario autenticado.
    PATCH /api/v1/users/me/ — Actualiza campos de Individual (perfil personal).
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return IndividualSerializer
        return UserDetailSerializer
    
    def update(self, request, *args, **kwargs):
        individual = request.user.individual
        serializer = IndividualSerializer(
            individual,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
