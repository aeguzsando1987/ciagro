# apps/users/models.py
# Custom User Model — placeholder para Fase 0.
# IMPORTANTE: Debe existir ANTES de la primera migración.
# Se expandirá completamente en Fase 1.

from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """
    Custom User que extiende AbstractUser de Django.
    Placeholder mínimo para permitir la migración inicial.
    Los campos adicionales del DBML (uuid pk, status, etc.) se agregan en Fase 1.
    """
    class Meta:
        db_table = "users"  # Nombre de la tabla en la base de datos
