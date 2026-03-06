import csv
import io
import tempfile

from django.contrib import admin
from django.forms import BaseInlineFormSet
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html

from apps.datalayers.models import DataLayer, DataLayerHeader, DataLayerPoints
from apps.datalayers.widgets import DefinitionSchemeWidget, EvaluationSchemeWidget


# ---------------------------------------------------------------------------
# Helper compartido: genera un HttpResponse CSV a partir de un header y sus puntos.
# Incluye comentarios de metadatos del header en las primeras líneas.
# ---------------------------------------------------------------------------

def _build_csv_response(header, points):
    """
    Genera la descarga CSV de los DataLayerPoints de un DataLayerHeader.

    Formato de salida:
        # datalayer: SUELO-2024
        # plot: PLT-001
        # import_date: 2024-03-15
        # crop: Maiz Blanco
        lat,lon,captured_at,pH,C,N,...
        23.56,-104.12,2024-03-01,6.8,1.23,...
    """
    # Recolectar claves JSONB únicas preservando orden de inserción
    jsonb_keys = list(dict.fromkeys(
        key
        for point in points
        for key in (point.raw_data or {}).keys()
    ))

    # Nombre de archivo descriptivo
    dl_code   = header.datalayer.code if header.datalayer_id else "datalayer"
    plot_code = header.plot.code if header.plot_id else "sin-plot"
    filename  = f"{dl_code}_{plot_code}_{header.import_date}.csv"

    buffer = io.StringIO()
    writer = csv.writer(buffer)

    # Filas de metadatos del header (comentarios legibles)
    writer.writerow([f"# datalayer: {dl_code}"])
    writer.writerow([f"# plot: {plot_code}"])
    writer.writerow([f"# import_date: {header.import_date}"])
    crop_name = header.crop.name if header.crop_id else "N/A"
    writer.writerow([f"# crop: {crop_name}"])

    # Fila de encabezado de columnas
    writer.writerow(["lat", "lon", "captured_at"] + jsonb_keys)

    # Filas de datos
    for point in points:
        lon, lat = point.geom.coords  # GeoJSON: (longitude, latitude)
        raw = point.raw_data or {}
        writer.writerow(
            [lat, lon, point.captured_at] + [raw.get(k, "") for k in jsonb_keys]
        )

    buffer.seek(0)
    response = HttpResponse(buffer, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@admin.register(DataLayer)
class DatalayerAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "created_at"]
    search_fields = ["code", "name"]
    ordering = ["created_at"]
    readonly_fields = ["created_at"]

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        """
        Aplica widget personalizado según el nombre del campo JSONB.
        formfield_for_dbfield (no formfield_overrides) porque necesitamos
        un widget DISTINTO para cada campo JSONField.
        """
        if db_field.name == "definition_scheme":
            kwargs["widget"] = DefinitionSchemeWidget()
        elif db_field.name == "evaluation_scheme":
            kwargs["widget"] = EvaluationSchemeWidget()
        return super().formfield_for_dbfield(db_field, request, **kwargs)


class DataLayerPointsFormSet(BaseInlineFormSet):
    """
    FormSet personalizado que limita la visualización a 50 puntos.

    El slice se aplica AQUÍ (después de que BaseInlineFormSet.__init__ aplica
    el filtro por header_id). Si se aplicara en get_queryset del Inline (antes
    del filtro del padre), Django lanzaría TypeError al intentar filtrar un
    queryset ya cortado.

    Se guarda el queryset recortado en self._qs_sliced para que todas las
    llamadas internas (initial_form_count, _construct_form) usen el mismo
    objeto QuerySet — esto comparte el _result_cache de Django y evita que
    cada acceso [i] lance una consulta SQL independiente.
    """
    def get_queryset(self):
        if not hasattr(self, "_qs_sliced"):
            self._qs_sliced = super().get_queryset()[:50]
        return self._qs_sliced


class DataLayerPointsInline(admin.TabularInline):
    model            = DataLayerPoints
    formset          = DataLayerPointsFormSet
    extra            = 0
    can_delete       = False  # los puntos son inmutables una vez cargados
    show_change_link = True
    readonly_fields  = ["id", "plot", "geom", "captured_at", "raw_data"]
    fields           = ["id", "plot", "geom", "captured_at", "raw_data"]
    verbose_name_plural = "Puntos de datos (primeros 50 — usar /points/ para ver todos)"

    def has_add_permission(self, request, obj=None):
        """Los puntos solo se crean vía importación CSV (Celery). No desde el admin."""
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).order_by("-captured_at")


@admin.register(DataLayerHeader)
class DataLayerHeaderAdmin(admin.ModelAdmin):
    list_display    = ["id", "datalayer", "plot", "crop", "import_date", "points_count", "created_at"]
    list_filter     = ["datalayer", "crop", "import_date"]
    search_fields   = ["datalayer__code", "datalayer__name", "plot__code", "crop__name"]
    ordering        = ["-import_date"]
    readonly_fields = ["id", "created_at", "import_csv_link", "export_csv_link", "locked_notice"]
    raw_id_fields   = ["task", "plot"]  # UUID FKs — evita dropdown con todos los registros
    inlines         = [DataLayerPointsInline]
    fieldsets = [
        ("Acciones e identificación", {
            # Primera pestaña: siempre visible. Contiene los botones de acción
            # y los metadatos de solo lectura del header.
            "fields": ["id", "locked_notice", "import_csv_link", "export_csv_link", "created_at"],
        }),
        ("Configuración del estudio", {
            "fields": ["datalayer", "plot", "crop", "task", "import_date"],
        }),
    ]

    # ------------------------------------------------------------------
    # B2: Inmutabilidad post-import
    # Campos que se bloquean cuando ya existen puntos cargados.
    # Solo import_date queda editable para correcciones de fecha.
    # ------------------------------------------------------------------
    _LOCKED_FIELDS = ["task", "plot", "crop", "datalayer"]

    def get_readonly_fields(self, request, obj=None):
        base = list(super().get_readonly_fields(request, obj))
        if obj and obj.points.count() > 0:
            return list(set(base + self._LOCKED_FIELDS))
        return base

    @admin.display(description="Estado de importación")
    def locked_notice(self, obj):
        """Banner informativo: muestra si el header está bloqueado o libre."""
        if not obj or not obj.pk:
            return "Nuevo header — todos los campos editables."
        count = obj.points.count()
        if count > 0:
            return format_html(
                '<span style="color:#c0392b;font-weight:bold">'
                "⛔ Header bloqueado — {:,} puntos importados. "
                "Solo se puede editar la fecha de importación."
                "</span>",
                count,
            )
        return format_html(
            '<span style="color:#27ae60">✅ Sin puntos — todos los campos editables.</span>'
        )

    # ------------------------------------------------------------------
    # URL personalizada: /admin/datalayers/datalayerheader/<pk>/import-csv/
    # ------------------------------------------------------------------

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<uuid:pk>/import-csv/",
                self.admin_site.admin_view(self.import_csv_view),
                name="datalayers_datalayerheader_import_csv",
            ),
            path(
                "<uuid:pk>/export-csv/",
                self.admin_site.admin_view(self.export_csv_view),
                name="datalayers_datalayerheader_export_csv",
            ),
        ]
        return custom + urls

    def import_csv_view(self, request, pk):
        """
        Vista admin que encola la importación de puntos para un header existente.
        Separa responsabilidades: crear el header (admin estándar) vs cargar puntos (esta vista).
        """
        from apps.datalayers.tasks import import_csv_to_datalayer

        header = get_object_or_404(DataLayerHeader, pk=pk)
        change_url = reverse("admin:datalayers_datalayerheader_change", args=[pk])

        if request.method == "POST":
            csv_file = request.FILES.get("csv_file")
            if not csv_file:
                self.message_user(request, "Selecciona un archivo CSV.", level="error")
            else:
                suffix = f"_{header.id}.csv"
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, mode="wb") as tmp:
                    for chunk in csv_file.chunks():
                        tmp.write(chunk)
                    tmp_path = tmp.name
                import_csv_to_datalayer.delay(str(header.id), tmp_path)
                self.message_user(
                    request,
                    f"Importación encolada para {header}. Los puntos aparecerán en breve.",
                )
                return HttpResponseRedirect(change_url)

        context = {
            **self.admin_site.each_context(request),
            "header": header,
            "change_url": change_url,
            "title": f"Importar CSV → {header}",
            "opts": self.model._meta,
        }
        return TemplateResponse(
            request,
            "admin/datalayers/datalayerheader/import_csv.html",
            context,
        )

    def export_csv_view(self, request, pk):
        """
        Descarga directa del CSV de puntos para un DataLayerHeader.
        No requiere template — devuelve el archivo inmediatamente.
        """
        header = get_object_or_404(
            DataLayerHeader.objects.select_related("datalayer", "plot", "crop"),
            pk=pk,
        )
        points = list(
            header.points.all().order_by("captured_at")
        )
        if not points:
            self.message_user(request, "Este header no tiene puntos cargados.", level="warning")
            return HttpResponseRedirect(
                reverse("admin:datalayers_datalayerheader_change", args=[pk])
            )
        return _build_csv_response(header, points)

    # ------------------------------------------------------------------
    # Post-save: redirigir al importador CSV tras crear un header nuevo
    # ------------------------------------------------------------------

    def response_add(self, request, obj, post_url_continue=None):
        """Tras crear un DataLayerHeader, ir directo a la pantalla de importación CSV."""
        url = reverse("admin:datalayers_datalayerheader_import_csv", args=[obj.pk])
        self.message_user(request, f"Header creado. Carga el CSV para: {obj}.")
        return HttpResponseRedirect(url)

    # ------------------------------------------------------------------
    # Métodos de display
    # ------------------------------------------------------------------

    @admin.display(description="Puntos")
    def points_count(self, obj):
        return obj.points.count()

    @admin.display(description="Importar puntos")
    def import_csv_link(self, obj):
        """Botón visible en el change form para lanzar la importación de CSV."""
        if not obj.pk:
            return "Guarda el header primero para habilitar la importación."
        url = reverse("admin:datalayers_datalayerheader_import_csv", args=[obj.pk])
        return format_html(
            '<a class="button" href="{}">📂 Importar puntos CSV</a>',
            url,
        )

    @admin.display(description="Exportar puntos")
    def export_csv_link(self, obj):
        """Botón visible en el change form para descargar los puntos como CSV."""
        if not obj.pk:
            return "Guarda el header primero."
        count = obj.points.count()
        if count == 0:
            return "Sin puntos cargados — no hay datos para exportar."
        url = reverse("admin:datalayers_datalayerheader_export_csv", args=[obj.pk])
        # Nota: format_html convierte todos los args a str via conditional_escape antes
        # de aplicar el format spec. {count:,} fallaría porque recibe "440" (str), no 440 (int).
        # Formateamos el número ANTES de pasarlo a format_html.
        count_fmt = f"{count:,}"
        return format_html(
            '<a class="button" href="{}">⬇️ Exportar {} puntos a CSV</a>',
            url,
            count_fmt,
        )


@admin.register(DataLayerPoints)
class DataLayerPointsAdmin(admin.ModelAdmin):
    list_display         = ["id", "header", "plot", "captured_at"]
    list_filter          = ["captured_at"]
    search_fields        = ["header__datalayer__code", "plot__code"]
    ordering             = ["-captured_at"]
    readonly_fields      = ["id", "geom"]   # geom como WKT — solo lectura sin GISModelAdmin
    raw_id_fields        = ["header", "plot"]
    list_select_related  = True             # evita N+1 al listar header y plot
    list_per_page        = 50              # tabla puede tener 60k+ filas

    def has_change_permission(self, request, obj=None):
        """Los puntos de datos son inmutables — no se editan una vez creados."""
        if obj is not None:
            return False
        return super().has_change_permission(request)
