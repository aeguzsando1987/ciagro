# apps/users/models.py
import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.core.models import BaseAuditModel


class User(AbstractUser):
    """
    Custom User. Extiende AbstractUser para conservar el sistema de auth de Django.
    Agrega: UUID pk, status de negocio, y FK a UserRole para RBAC.
    """
    STATUS_ACTIVE = "active"
    STATUS_DISABLED = "disabled"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Activo"),
        (STATUS_DISABLED, "Desactivado"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    user_role = models.ForeignKey(
        "UserRole",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="users",
    )

    def __str__(self):
        return self.username

    class Meta:
        db_table = "users"


class UserRole(models.Model):
    """
    Modelo de rol de usuario

    Args:
        models (_type_): _description_

    Returns:
        _type_: _description_
    """
    # PK explicito
    id = models.AutoField(primary_key=True)
    # Titulo para el rol (ej. "Gerente", "Administrador", etc.)
    role_name = models.CharField(max_length=50, unique=True)
    # Nivel jerarquico para comparaciones en clases de permisos DRF.
    # 1=Guest, 2=Technician, 3=Supervisor, 4=Gerente, 5=SuperAdmin
    level = models.PositiveSmallIntegerField(default=1, unique=True)

    def __str__(self):
        return self.role_name

    class Meta:
        db_table = "user_roles"
        
        
class WorkRole(models.Model):
    """
    Modelo de rol de trabajo

    Args:
        models (_type_): _description_

    Returns:
        _type_: _description_
    """
    id = models.AutoField(primary_key=True)
    work_name = models.CharField(max_length=50, unique=True)
    activity_description = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return self.work_name

    class Meta:
        db_table = "work_roles"
        
        
class Individual(BaseAuditModel):
    """
    Perfil humano vinculado 1:1 a User.
    Almacena datos personales, de contacto y rol laboral.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="individual",
    )
    work_role = models.ForeignKey(
        "WorkRole",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="individuals",
    )
    
    # Datos personales del usuario
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    phone = models.CharField(max_length=20, null=True, blank=True)
    photo_url = models.URLField(null=True, blank=True)
    personal_email = models.EmailField(null=True, blank=True)
    address_line_1 = models.CharField(max_length=100, null=True, blank=True)
    address_line_2 = models.CharField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length=50, null=True, blank=True)
    # state FK Cuando se implemente la parte de goeografía basica
    # country FK Cuando se implemente la parte de goeografía basica
    postal_code = models.CharField(max_length=10, null=True, blank=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    class Meta:
        db_table = "individuals"
