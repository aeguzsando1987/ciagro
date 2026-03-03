import uuid
from datetime import date
from django.db import models
from django.contrib.gis.db.models import PointField
from django.contrib.postgres.indexes import GinIndex


class DataLayer(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=100, unique=True)
    definition_scheme = models.JSONField(
        default=dict,
        blank=True,
        help_text="Contrato de ingesta: campos obligatorios, tipos y alias para parseo de datos de CSV/sensores."
    )
    evaluation_scheme = models.JSONField(
        default=dict,
        blank=True,
        help_text="Contrato agronomico: ejes kiviat, rangos de colorimetria y preguntas manuales."
    )
    attachments_url = models.JSONField(default=list, blank=True)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    class Meta:
        db_table = "datalayers"
        ordering = ["name"]


class DataLayerHeader(models.Model):
    """
    Agrupa un lote de puntos de datos (ej: 60,000 puntos de un mapa de rendimiento).
    Representa una importación de datos para un lote, cultivo y capa de datos específicos.
    Puede vincularse opcionalmente a una FieldTask planificada.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(
        "field_ops.FieldTask",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="datalayer_headers",
        help_text="Opcional: tarea planificada que contempla la importación.",
    )
    plot = models.ForeignKey(
        "geo_assets.Plot",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="datalayer_headers",
        verbose_name="Parcela",
        help_text=(
            "Lote geográfico al que pertenece este conjunto de puntos.\n "
            "NOTA: Si vincula una actividad planificada, se hereda automáticoamente la parcela."
        ),
    )
    crop = models.ForeignKey(
        "field_ops.CropCatalog",
        on_delete=models.PROTECT,
        related_name="datalayer_headers",
        verbose_name="Cultivo",
        help_text="Opcional: Cultivo asociado al conjunto de datos.\n NOTA: no es necesario si vincula una task.",
    )
    datalayer = models.ForeignKey(
        DataLayer,
        on_delete=models.PROTECT,
        related_name="headers",
        verbose_name="Tipo de analisis/ingesta",
        help_text="Contrato de datos (definition_scheme) que valida esta importación.",
    )
    import_date = models.DateField(
        default=date.today,
        verbose_name="Fecha de importación",
        help_text="Fecha en que se realizó o corresponde la importación.",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")

    def save(self, *args, **kwargs):
        # Denormalización: si hay task y plot no fue provisto, se hereda de task.plot
        if self.task_id and self.plot_id is None:
            self.plot_id = self.task.plot_id
        super().save(*args, **kwargs)

    def __str__(self):
        return f"DLHeader({self.datalayer.code} | plot={self.plot_id} | {self.import_date})"

    class Meta:
        db_table = "datalayer_headers"
        ordering = ["-import_date"]
        indexes = [
            models.Index(fields=["task"],        name="idx_dlheaders_task"),
            models.Index(fields=["plot"],        name="idx_dlheaders_plot"),
            models.Index(fields=["datalayer"],   name="idx_dlheaders_datalayer"),
            models.Index(fields=["import_date"], name="idx_dlheaders_import_date"),
        ]


class DataLayerPoints(models.Model):
    """
    Puntos de datos (ej: 60,000 puntos de una toma de analisis, por ejemplo un mapeo de suelo).
    Representa una importación de datos para un lote, cultivo y capa de datos específicos.
    Siempre se vincula a un DataLayerHeader. 
    Puede vincularse opcionalmente a una FieldTask planificada.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    header = models.ForeignKey(
        DataLayerHeader,
        on_delete=models.CASCADE,
        related_name="points",
        help_text="Lote de importación al que pertenece este punto."
    )
    plot = models.ForeignKey(
        "geo_assets.Plot",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="data_points",
        help_text=(
            "Lote geográfico (denormalizado) al que pertenece este punto. "
            "Si se vincula una task, se hereda automáticamente de header.plot."
            "Para consultas directas sin JOINs"
        ),
    )
    geom = PointField(
        srid=4326,
        help_text="Coordenada geografica del punto capturado (WGS84). GiST automaticamente indexado.",
    )
    captured_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha, hora y segundo en la que se capturó el punto de datos."
    )
    raw_data = models.JSONField(
        default=dict,
        help_text=("JSON con los datos necesarios capturados en el punto."
                "Estructura validad en el definition_scheme de DataLayer correspondiente.")
    )
    
    def save(self, *args, **kwargs):
        # Denormalización: hereda plot del header si no fue provisto en CSV
        # No aplica en bulk_create() - Esta tarea se asigna con Celery explicitamente
        if self.header_id and self.plot_id is None:    
            self.plot_id = self.header.plot_id
        super().save(*args, **kwargs)
        
    
    def __str__(self):
        return f"DLPoint(header: {self.header_id} | plot={self.plot_id} | {self.captured_at})"
    
    class Meta:
        db_table = "datalayer_points"
        ordering = ["-captured_at"]
        indexes = [
            models.Index(fields=["header"], name="idx_dlpoints_header"),
            models.Index(fields=["plot", "captured_at"], name="idx_dlpoints_plot_captured_at"),
            GinIndex(fields=["raw_data"], name="idx_dlpoints_raw_data")
            # GiST sobre 'geom' lo genera automaticamente GeoDjango (spatial_index=True por defecto)
        ]