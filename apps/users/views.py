# apps/users/views.py
from django.contrib.auth import update_session_auth_hash
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from drf_spectacular.utils import extend_schema, inline_serializer
from drf_spectacular.types import OpenApiTypes
from rest_framework import serializers as drf_serializers

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


@extend_schema(
    tags=["auth"],
    summary="Login — obtener tokens JWT",
    description=(
        "Autentica con `username` y `password`. "
        "Retorna `access` (vida 5 min) y `refresh` (vida 7 días). "
        "El `access` token incluye los claims `role_name` y `role_level`.\n\n"
        "**En Swagger UI**: una vez obtenido el `access` token, pulsa **Authorize** "
        "(candado en la parte superior) y pégalo como `Bearer <access_token>`."
    ),
)
class LoginView(TokenObtainPairView):
    serializer_class = CIAgroTokenObtainPairSerializer


@extend_schema(
    tags=["auth"],
    summary="Logout — invalidar refresh token",
    description=(
        "Añade el `refresh` token a la blacklist de simplejwt. "
        "Después de esto, ese refresh token no puede usarse para obtener nuevos access tokens. "
        "El cliente debe también borrar el access token de su almacenamiento local."
    ),
    request=inline_serializer(
        name="LogoutRequest",
        fields={"refresh": drf_serializers.CharField(help_text="Refresh token a invalidar")},
    ),
    responses={204: None, 400: OpenApiTypes.OBJECT},
)
class LogoutView(APIView):
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


@extend_schema(
    tags=["auth"],
    summary="Cambiar contraseña",
    request=inline_serializer(
        name="ChangePasswordRequest",
        fields={
            "old_password": drf_serializers.CharField(),
            "new_password": drf_serializers.CharField(),
        },
    ),
    responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
)
class ChangePasswordView(APIView):
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


@extend_schema(
    tags=["auth"],
    summary="Registrar usuario (admin)",
    description="Crea un User + Individual. El usuario recibirá `requires_password_change=True`. Solo SuperAdmin.",
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


@extend_schema(
    tags=["auth"],
    summary="Auto-registro público",
    description="Crea un usuario sin rol asignado. Disponible sin autenticación (AllowAny).",
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
        
        
@extend_schema(tags=["users"], summary="Listar roles de acceso (UserRole)")
class UserRoleListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = UserRole.objects.all().order_by("level")
    serializer_class = UserRoleSerializer


@extend_schema(tags=["users"], summary="Listar roles laborales (WorkRole)")
class WorkRoleListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = WorkRole.objects.all().order_by("work_name")
    serializer_class = WorkRoleSerializer


@extend_schema(tags=["users"], summary="Listar usuarios activos")
class UserListView(generics.ListAPIView):
    permission_classes = [IsSuperAdmin]
    queryset = User.objects.filter(is_deleted=False).select_related("user_role", "individual").order_by("username")
    serializer_class = UserDetailSerializer


@extend_schema(tags=["users"], summary="Eliminar usuario (soft delete)")
class UserDestroyView(SoftDeleteMixin, generics.DestroyAPIView):
    permission_classes = [IsSuperAdmin]
    queryset = User.objects.filter(is_deleted=False)


@extend_schema(
    tags=["users"],
    summary="Listar asignaciones usuario -unidad",
    description="Filtros opcionales: `?user=<uuid>` y `?agro_unit=<uuid>`.",
)
class UserAssignmentListView(generics.ListAPIView):
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


@extend_schema(tags=["users"], summary="Crear asignación usuario -unidad")
class UserAssignmentCreateView(generics.CreateAPIView):
    permission_classes = [IsSuperAdmin]
    queryset = UserAssignment.objects.all()
    serializer_class = UserAssignmentSerializer


@extend_schema(tags=["users"], summary="Eliminar asignación usuario -unidad")
class UserAssignmentDestroyView(generics.DestroyAPIView):
    permission_classes = [IsSuperAdmin]
    queryset = UserAssignment.objects.all()


@extend_schema(
    tags=["users"],
    summary="Perfil propio (GET/PATCH)",
    description=(
        "`GET` retorna el perfil completo del usuario autenticado. "
        "`PATCH` actualiza campos del `Individual` asociado (nombre, teléfono, etc.)."
    ),
)
class UserMeView(generics.RetrieveUpdateAPIView):
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
