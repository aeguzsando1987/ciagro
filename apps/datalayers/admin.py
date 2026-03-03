import tempfile

from django.contrib import admin
from django.forms import BaseInlineFormSet
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html

from apps.datalayers.models import DataLayer, DataLayerHeader, DataLayerPoints
from apps.datalayers.widgets import DefinitionSchemeWidget, EvaluationSchemeWidget


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
    El slice se aplica AQUÍ (después de que Django filtra por header_id),
    no en get_queryset del Inline (donde aún no se ha aplicado el filtro del padre
    y el slice provocaría un TypeError al intentar filtrar un queryset ya cortado).
    """
    def get_queryset(self):
        return super().get_queryset()[:50]


class DataLayerPointsInline(admin.TabularInline):
    model            = DataLayerPoints
    formset          = DataLayerPointsFormSet
    extra            = 0
    can_delete       = False  # los puntos son inmutables una vez cargados
    max_num          = 0      # no permite agregar puntos desde el inline (usar /headers/import/)
    show_change_link = True
    readonly_fields  = ["id", "plot", "geom", "captured_at", "raw_data"]
    fields           = ["id", "plot", "geom", "captured_at", "raw_data"]
    verbose_name_plural = "Puntos de datos (primeros 50 — usar /points/ para ver todos)"

    def get_queryset(self, request):
        return super().get_queryset(request).order_by("-captured_at")


@admin.register(DataLayerHeader)
class DataLayerHeaderAdmin(admin.ModelAdmin):
    list_display    = ["id", "datalayer", "plot", "crop", "import_date", "points_count", "created_at"]
    list_filter     = ["datalayer", "crop", "import_date"]
    search_fields   = ["datalayer__code", "datalayer__name", "plot__code", "crop__name"]
    ordering        = ["-import_date"]
    readonly_fields = ["id", "created_at", "import_csv_link"]
    raw_id_fields   = ["task", "plot"]  # UUID FKs — evita dropdown con todos los registros
    inlines         = [DataLayerPointsInline]

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
