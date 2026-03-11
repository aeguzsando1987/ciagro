from django.db import models
import uuid
from django.core.validators import RegexValidator
from apps.datalayers.models import DataLayer



class CropCatalog(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(
        max_length=200,
        unique=True,
        help_text="Variedad de cultivo (ej: Manzana Verde, Mango Manila, Moringa, Calabacin).",
    )
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
        

class FieldTaskReport(models.Model):
    """
    Reporte de cierre de una FieldTask. Estructura híbrida:
    - summary_data: calculado automáticamente por GenerateReportView (estadísticas de DataLayerPoints)
    - El resto: completado manualmente por el técnico/ingeniero desde admin/UI
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    task = models.OneToOneField(
        FieldTask,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="report",
        help_text="Tarea de campo que origina este reporte. 1:1 — cada task tiene máximo un reporte.",
    )
    plot = models.ForeignKey(
        "geo_assets.Plot",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="task_reports",
        help_text="Lote denormalizado desde task.plot para consultas rápidas.",
    )
    evaluator = models.ForeignKey(
        "users.Individual",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="evaluated_reports",
        help_text="Técnico o ingeniero que generó/validó el reporte.",
    )

    # --- Calculado automáticamente por GenerateReportView ---
    summary_data = models.JSONField(
        default=dict,
        help_text="Estadísticas calculadas automáticamente: conteo, min/max/avg por campo numérico de parameters.",
    )
    report_date = models.DateField(
        auto_now_add=True,
        help_text="Fecha de generación del reporte (automática).",
    )

    # --- Completado manualmente por el técnico/ingeniero ---
    evaluation_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Scores Kiviat, etapa fisiológica GDD y ajustes manuales a la colorimetría.",
    )
    scan_date = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha en que se realizó la toma de datos en campo.",
    )
    report_score = models.IntegerField(
        null=True,
        blank=True,
        help_text="Calificación general del desempeño (1-10).",
    )
    main_causes = models.TextField(null=True, blank=True)
    summary_1 = models.TextField(null=True, blank=True, help_text="Situación actual observada.")
    summary_2 = models.TextField(null=True, blank=True, help_text="Causas identificables y factores externos.")
    conclusion = models.TextField(null=True, blank=True, help_text="Dictamen final del ingeniero.")
    internal_comments = models.TextField(null=True, blank=True, help_text="Notas privadas para nivel gerencial.")
    map_url = models.URLField(null=True, blank=True, help_text="URL del snapshot del mapa de calor.")
    attachments_url = models.JSONField(default=list, blank=True, help_text="Array de URLs de fotos de evidencia.")
    is_valid = models.BooleanField(default=True)
    validation_token = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self):
        return f"Reporte({self.task} | {self.report_date})"

    class Meta:
        db_table = "field_task_reports"
        ordering = ["-report_date"]
        indexes = [
            models.Index(fields=["task"],        name="idx_ftreports_task"),
            models.Index(fields=["plot"],        name="idx_ftreports_plot"),
            models.Index(fields=["report_date"], name="idx_ftreports_date"),
        ]


class TaskReportIssue(models.Model):
    """
    Issue de atención derivado de un FieldTaskReport.
    El técnico/ingeniero los crea manualmente al revisar el reporte.
    Un reporte puede generar N issues que el equipo debe resolver antes del cierre.
    """
    SEVERITY_LOW = "low"
    SEVERITY_MEDIUM = "medium"
    SEVERITY_HIGH = "high"
    SEVERITY_CHOICES = [
        (SEVERITY_LOW,    "Baja"),
        (SEVERITY_MEDIUM, "Media"),
        (SEVERITY_HIGH,   "Alta"),
    ]

    STATUS_PENDING    = "pendiente"
    STATUS_IN_PROGRESS = "en_progreso"
    STATUS_UNSOLVABLE = "irresoluble"
    STATUS_SOLVED     = "solucionada"
    STATUS_CHOICES = [
        (STATUS_PENDING,     "Pendiente"),
        (STATUS_IN_PROGRESS, "En progreso"),
        (STATUS_UNSOLVABLE,  "Irresoluble"),
        (STATUS_SOLVED,      "Solucionada"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    report = models.ForeignKey(
        FieldTaskReport,
        on_delete=models.CASCADE,
        related_name="issues",
        help_text="Reporte del que se deriva este issue.",
    )

    issue_title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    agro_activity = models.CharField(max_length=100, null=True, blank=True,
                                     help_text="Actividad agronómica relacionada (valores definidos en config).")
    issue_type = models.CharField(max_length=100, null=True, blank=True,
                                  help_text="Tipo de issue (valores definidos en config).")
    probability = models.FloatField(null=True, blank=True,
                                    help_text="Probabilidad de ocurrencia (0.0 - 1.0).")
    severity_alert = models.CharField(
        max_length=10, choices=SEVERITY_CHOICES, default=SEVERITY_MEDIUM,
    )
    expected_solution = models.TextField(null=True, blank=True)
    reached_solution = models.TextField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING,
    )
    is_ruled = models.BooleanField(
        default=False,
        help_text="True cuando el issue está resuelto o marcado como irresoluble.",
    )
    identification_date = models.DateField(null=True, blank=True)
    solution_date = models.DateField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.issue_title} [{self.get_severity_alert_display()}]"

    class Meta:
        db_table = "task_report_issues"
        ordering = ["-severity_alert", "status"]
        indexes = [
            models.Index(fields=["report"],   name="idx_tri_report"),
            models.Index(fields=["status"],   name="idx_tri_status"),
            models.Index(fields=["is_ruled"], name="idx_tri_is_ruled"),
        ]
