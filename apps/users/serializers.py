# apps/users/serializers.py
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


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

        return token