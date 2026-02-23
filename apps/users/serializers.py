# apps/users/serializers.py
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from django.db import transaction
from apps.users.models import Individual, User, UserRole, WorkRole


class CIAgroTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Extiende el serializer base de simplejwt para agregar claims personalizados
    al payload del access token: email, username, rol y nivel jerarquico.

    El cliente recibe esta info directamente en el token, sin request extra.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Claims de identidad
        token["email"] = user.email
        token["username"] = user.username
        token["status"] = user.status

        # Claims de rol — None si el usuario no tiene rol asignado
        if user.user_role:
            token["role_name"] = user.user_role.role_name
            token["role_level"] = user.user_role.level
        else:
            token["role_name"] = None
            token["role_level"] = 0

        token["requires_password_change"] = user.requires_password_change

        return token
    
class AdminRegisterSerializer(serializers.Serializer):
    # Campos de usuario
    username = serializers.CharField(max_length=20)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True) # No se devuelve en la respuesta
    user_role = serializers.PrimaryKeyRelatedField(
        queryset=UserRole.objects.all(),
        required=False
    )
    
    # Campos de perfil (Individual)
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    phone = serializers.CharField(required=False, allow_blank=True)
    work_role = serializers.PrimaryKeyRelatedField(
        queryset=WorkRole.objects.all(),
        required=False
    )
    
    def create(self, validated_data):
        with transaction.atomic():
            user = User.objects.create_user(
                username=validated_data["username"],
                email=validated_data["email"],
                password=validated_data["password"],
                user_role=validated_data.get("user_role"),
                requires_password_change=True,
            )
            Individual.objects.create(
                user=user,
                first_name=validated_data["first_name"],
                last_name=validated_data["last_name"],
                phone=validated_data.get("phone"),
                work_role=validated_data.get("work_role"),
            )
        return user
    
    
class PublicRegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=50)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    phone = serializers.CharField(required=False, allow_blank=True)
    
    def create(self, validated_data):
        with transaction.atomic():
            user = User.objects.create_user(
                username=validated_data["username"],
                email=validated_data["email"],
                password=validated_data["password"],
            )
            Individual.objects.create(
                user=user,
                first_name=validated_data["first_name"],
                last_name=validated_data["last_name"],
                phone=validated_data.get("phone"),
            )
        return user