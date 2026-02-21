# apps/core/models.py
# Modelo base abstracto. Todas las entidades del sistema heredan de aquí.
import uuid
from django.db import models
from django.conf import settings


class BaseAuditModel(models.Model):
    """
    Modelo base abstracto. Todas las entidades del sistema heredan de aqui.
    UUID para identificar de manera unica cada entidad.
    Args:
        models (_type_): _description_
    """
    # Identificador unico
    # uuid4 para generacion de uuid aleatorio basado en timestamp
    # no modificable
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # timestamps
    # auto_now_add para el momento de creacion
    # auto_now para el momento de actualizacion
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    # soft delete
    is_deleted = models.BooleanField(default=False)
    
    # user audit
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="%(app_label)s_%(class)s_created_by",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="%(app_label)s_%(class)s_updated_by",
    )
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="%(app_label)s_%(class)s_deleted_by",
    )
    
    class Meta:
        abstract = True
