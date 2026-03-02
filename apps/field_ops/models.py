from django.db import models
import uuid
from django.core.validators import RegexValidator
from apps.datalayers.models import DataLayer


class CropCatalog(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(null=True, blank=True)
    photo_url = models.URLField(max_length=500, null=True, blank=True)
    additional_params = models.JSONField(default=dict, blank=True)
    attachments_url = models.JSONField(default=list, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'crop_catalog'
        ordering = ['name']


class PestCatalog(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200, unique=True)
    default_crop = models.ForeignKey(
        CropCatalog,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="common_pests"
    )
    description = models.TextField(null=True, blank=True)
    ref_value = models.IntegerField(null=True, blank=True, help_text="Valor de referencia como umbral de tolerancia")
    photo_url = models.URLField(max_length=500, null=True, blank=True)
    additional_params = models.JSONField(default=dict, blank=True)
    attachments_url = models.JSONField(default=list, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'pest_catalog'
        ordering = ['name']


class FieldTask(models.Model):

    STATUS_PENDING = "pending"
    STATUS_OPEN = "open"
    STATUS_PROCESSING = "processing"
    STATUS_COMPLETED = "completed"
    STATUS_EXPIRED = "expired"
    STATUS_CLOSED = "closed"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pendiente"),
        (STATUS_OPEN, "Abierto"),
        (STATUS_PROCESSING, "Procesando"),
        (STATUS_COMPLETED, "Completado"),
        (STATUS_EXPIRED, "Expirado"),
        (STATUS_CLOSED, "Cerrado"),
        (STATUS_CANCELLED, "Cancelado"),
    ]

    CYCLE_VALIDATOR = RegexValidator(
        regex=r'^\d{4}-[AB]$',
        message="Formato de ciclo inválido. Debe ser YYYY-A o YYYY-B (Ej. 2022-A)"
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Para la jerarquia de tareas
    parent_task = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subtasks"
    )

    voucher_code = models.CharField(max_length=50, null=True, blank=True)
    title = models.CharField(max_length=200, null=True, blank=True)
    cycle = models.CharField(
        max_length=10,
        validators=[CYCLE_VALIDATOR],
        null=True,
        blank=True
    )

    datalayer = models.ForeignKey(
        DataLayer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="field_tasks"
    )
    individual = models.ForeignKey(
        "users.Individual",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="field_tasks"
    )
    agro_unit = models.ForeignKey(
        "organizations.AgroUnit",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="field_tasks"
    )
    plot = models.ForeignKey(
        "geo_assets.Plot",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="field_tasks"
    )
    crop = models.ForeignKey(
        CropCatalog,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="field_tasks"
    )

    est_start_date = models.DateTimeField(null=True, blank=True)
    est_finish_date = models.DateTimeField(null=True, blank=True)
    actual_start_date = models.DateTimeField(null=True, blank=True)
    actual_finish_date = models.DateTimeField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    location_url = models.URLField(null=True, blank=True)
    attachments_url = models.JSONField(default=list, blank=True)

    def __str__(self):
        return self.voucher_code or str(self.id)

    class Meta:
        db_table = 'field_tasks'
        ordering = ['-est_start_date']
