# apps/core/models.py
# Modelo base abstracto. Todas las entidades del sistema heredan de aquí.
import uuid
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


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


def _attachment_upload_path(instance, filename):
    """Organiza los archivos por tipo de modelo: media/attachments/<model>/<filename>."""
    model_name = instance.content_type.model if instance.content_type_id else "misc"
    return f"attachments/{model_name}/{filename}"


class Attachment(models.Model):
    """
    Archivo adjunto genérico que puede vincularse a cualquier modelo del proyecto.

    Usa GenericForeignKey para no depender de FKs específicas a cada modelo.
    Al guardar o borrar un Attachment, sincroniza automáticamente la lista
    attachments_url del objeto padre (si el campo existe).

    El archivo se almacena en MEDIA_ROOT/attachments/<model>/<filename>.
    La URL pública (/media/attachments/...) permite descargar o visualizar
    el archivo directamente en el browser (PDFs se abren, otros se descargan).
    """

    # ── Relación genérica ──────────────────────────────────────────────────
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name="Tipo de objeto",
    )
    # CharField(40) soporta UUID (36 chars) e int PKs como string
    object_id = models.CharField(max_length=40, db_index=True, verbose_name="ID del objeto")
    content_object = GenericForeignKey("content_type", "object_id")

    # ── Archivo ───────────────────────────────────────────────────────────
    file = models.FileField(
        upload_to=_attachment_upload_path,
        verbose_name="Archivo",
    )
    filename = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Nombre del archivo",
        help_text="Se auto-completa con el nombre del archivo subido.",
    )

    # ── Auditoría ─────────────────────────────────────────────────────────
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Subido el")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="uploaded_attachments",
        verbose_name="Subido por",
    )

    def save(self, *args, **kwargs):
        # Auto-poblar filename desde el nombre del archivo al crear
        if self.file and not self.filename:
            self.filename = self.file.name.split("/")[-1]
        super().save(*args, **kwargs)
        self._sync_parent_urls()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        self._sync_parent_urls()

    def _sync_parent_urls(self):
        """
        Reconstruye attachments_url del objeto padre con las URLs de todos
        los Attachments activos. Usa update() directo para evitar recursión
        y no disparar otros hooks de save().
        """
        obj = self.content_object
        if obj is None or not hasattr(obj, "attachments_url"):
            return
        paths = list(
            Attachment.objects.filter(
                content_type_id=self.content_type_id,
                object_id=self.object_id,
            ).values_list("file", flat=True)
        )
        urls = [
            f"{settings.MEDIA_URL}{p}" if not p.startswith("/") else p
            for p in paths
        ]
        obj.__class__.objects.filter(pk=obj.pk).update(attachments_url=urls)

    def __str__(self):
        return self.filename or str(self.file)

    class Meta:
        db_table = "attachments"
        ordering = ["-uploaded_at"]
        verbose_name = "Archivo adjunto"
        verbose_name_plural = "Archivos adjuntos"
