# apps/datalayers/views.py
import csv
import io
import tempfile
from datetime import date
from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework import status as http_status
from django.http import HttpResponse
from drf_spectacular.utils import extend_schema, OpenApiParameter, inline_serializer
from drf_spectacular.types import OpenApiTypes
from rest_framework import serializers as drf_serializers
from apps.datalayers.models import DataLayer, DataLayerHeader, DataLayerPoints
from apps.datalayers.serializers import (
    DataLayerSerializer,
    DataLayerHeaderSerializer,
    DataLayerPointsSerializer,
)
from apps.datalayers.tasks import import_csv_to_datalayer
from apps.users.permissions import IsSuperAdmin, IsSupervisor, IsTechnician


# ---------------------------------------------------------------------------
# DataLayer — el contrato/esquema de captura. Solo SuperAdmin lo define.
# ---------------------------------------------------------------------------

@extend_schema(tags=["datalayers"], summary="Listar contratos de datos (DataLayer)")
class DataLayerListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = DataLayer.objects.all()
    serializer_class = DataLayerSerializer


@extend_schema(tags=["datalayers"], summary="Crear contrato de datos")
class DataLayerCreateView(generics.CreateAPIView):
    permission_classes = [IsSuperAdmin]
    queryset = DataLayer.objects.all()
    serializer_class = DataLayerSerializer


@extend_schema(tags=["datalayers"], summary="Detalle de un contrato de datos")
class DataLayerDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = DataLayer.objects.all()
    serializer_class = DataLayerSerializer


@extend_schema(tags=["datalayers"], summary="Actualizar contrato de datos")
class DataLayerUpdateView(generics.UpdateAPIView):
    permission_classes = [IsSuperAdmin]
    queryset = DataLayer.objects.all()
    serializer_class = DataLayerSerializer


# ---------------------------------------------------------------------------
# DataLayerHeader — encabezado de sesión de captura.
# Los técnicos crean y el supervisor puede corregir metadatos.
# ---------------------------------------------------------------------------

@extend_schema(tags=["datalayers"], summary="Listar encabezados de importación")
class DataLayerHeaderListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DataLayerHeaderSerializer

    def get_queryset(self):
        return DataLayerHeader.objects.select_related(
            "datalayer", "plot", "crop", "task"
        ).all()


@extend_schema(tags=["datalayers"], summary="Crear encabezado de importación")
class DataLayerHeaderCreateView(generics.CreateAPIView):
    permission_classes = [IsTechnician]
    queryset = DataLayerHeader.objects.all()
    serializer_class = DataLayerHeaderSerializer


@extend_schema(tags=["datalayers"], summary="Detalle de un encabezado de importación")
class DataLayerHeaderDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DataLayerHeaderSerializer

    def get_queryset(self):
        return DataLayerHeader.objects.select_related(
            "datalayer", "plot", "crop", "task"
        ).all()


@extend_schema(tags=["datalayers"], summary="Actualizar metadatos de encabezado")
class DataLayerHeaderUpdateView(generics.UpdateAPIView):
    permission_classes = [IsSupervisor]
    queryset = DataLayerHeader.objects.all()
    serializer_class = DataLayerHeaderSerializer


@extend_schema(
    tags=["datalayers"],
    summary="Importar puntos desde CSV (async)",
    description=(
        "Crea un `DataLayerHeader` y encola una tarea Celery que procesa el CSV "
        "en segundo plano y genera los `DataLayerPoints` en bulk.\n\n"
        "**Body** (`multipart/form-data`):\n"
        "- `task` *(UUID, opcional)* — tarea de campo que origina la importación\n"
        "- `datalayer` *(int, requerido)* — contrato de datos a aplicar\n"
        "- `crop` *(int, requerido)* — variedad de cultivo en el momento de captura\n"
        "- `import_date` *(date YYYY-MM-DD, requerido)* — fecha de la toma de muestras\n"
        "- `csv_file` *(file, requerido)* — CSV con columnas obligatorias: `lat`, `lon`; "
        "opcional: `captured_at`; columnas adicionales se mapean a `raw_data` JSONB segun `definition_scheme` del DataLayer\n\n"
        "**Responde 202 Accepted** de inmediato con `header_id` y `celery_task_id`. "
        "Los puntos se crean de forma asíncrona; consultar el listado de puntos con "
        "`GET /api/v1/datalayers/points/?header=<header_id>` para verificar el resultado."
    ),
    request=inline_serializer(
        name="ImportCSVRequest",
        fields={
            "task":        drf_serializers.UUIDField(required=False, help_text="UUID de la FieldTask (opcional)"),
            "datalayer":   drf_serializers.IntegerField(help_text="ID del DataLayer a aplicar"),
            "crop":        drf_serializers.IntegerField(help_text="ID del CropCatalog"),
            "import_date": drf_serializers.DateField(help_text="Fecha de captura YYYY-MM-DD"),
            "csv_file":    drf_serializers.FileField(help_text="Archivo CSV con columnas lat, lon [, captured_at] + raw_data"),
        },
    ),
    responses={
        202: inline_serializer(
            name="ImportCSVResponse",
            fields={
                "header_id":      drf_serializers.UUIDField(),
                "celery_task_id": drf_serializers.CharField(),
                "detail":         drf_serializers.CharField(),
            },
        ),
        400: OpenApiTypes.OBJECT,
        409: OpenApiTypes.OBJECT,
    },
)
class DataLayerHeaderImportView(APIView):
    permission_classes = [IsTechnician]
    parser_classes = [MultiPartParser]

    def post(self, request):
        csv_file = request.FILES.get("csv_file")
        if not csv_file:
            return Response(
                {"detail": "Se requiere el archivo csv_file."},
                status=http_status.HTTP_400_BAD_REQUEST,
            )

        # Guard: tarea cerrada no acepta nuevas importaciones (409 Conflict)
        task_id = request.data.get("task")
        if task_id:
            from apps.field_ops.models import FieldTask
            try:
                field_task = FieldTask.objects.get(id=task_id)
                if field_task.status == FieldTask.STATUS_CLOSED:
                    return Response(
                        {"detail": "No se puede importar datos a una tarea cerrada."},
                        status=http_status.HTTP_409_CONFLICT,
                    )
            except FieldTask.DoesNotExist:
                pass  # El serializer validará la FK

        # Crear el header síncronamente (rápido — sin puntos aún)
        serializer = DataLayerHeaderSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=http_status.HTTP_400_BAD_REQUEST)
        header = serializer.save()

        # Guardar el CSV en un archivo temporal con ruta conocida para Celery
        suffix = f"_{header.id}.csv"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, mode="wb") as tmp:
            for chunk in csv_file.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        # Encolar la tarea Celery (procesamiento async)
        task = import_csv_to_datalayer.delay(str(header.id), tmp_path)

        return Response(
            {
                "header_id": str(header.id),
                "celery_task_id": task.id,
                "detail": "Importación encolada correctamente.",
            },
            status=http_status.HTTP_202_ACCEPTED,
        )


# ---------------------------------------------------------------------------
# DataLayerPoints — puntos individuales de captura. Inmutables una vez cargados.
# Los técnicos crean puntos individuales (la carga masiva usa /headers/import/).
# ---------------------------------------------------------------------------

@extend_schema(
    tags=["datalayers"],
    summary="Listar puntos georreferenciados (DataLayerPoints)",
    description=(
        "Retorna los puntos de captura de muestras agricolas. Cada punto incluye:\n\n"
        "- `geom`: coordenadas WGS84 (EPSG:4326) — **Point** GeoJSON\n"
        "- `raw_data`: objeto JSONB con los atributos medidos en el punto "
        "(pH, C, N, NDVI, etc.) definidos por el `definition_scheme` del DataLayer asociado\n\n"
        "**Uso tipico para mapas de calor**: combinar `geom` (lat/lon) con el valor "
        "del atributo deseado de `raw_data` como intensidad en el visor geoespacial. "
        "La colorimetria se obtiene del `evaluation_scheme` del DataLayer filtrado.\n\n"
        "**Sin paginacion**: esta vista retorna todos los puntos del filtro activo "
        "(puede ser >60 000 registros). Siempre use al menos un filtro para acotar el resultado.\n\n"
        "**Ejemplo de `raw_data`**:\n"
        "```json\n"
        "{\"pH\": 6.8, \"C\": 1.23, \"N\": 0.15, \"NDVI\": 0.74}\n"
        "```"
    ),
    parameters=[
        OpenApiParameter(
            name="header",
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Filtra por UUID del DataLayerHeader (sesion de captura).",
        ),
        OpenApiParameter(
            name="plot",
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Filtra por UUID del Plot (lote/parcela).",
        ),
        OpenApiParameter(
            name="ranch",
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Filtra por UUID del Ranch. Incluye todos los lotes del rancho.",
        ),
        OpenApiParameter(
            name="agro_unit",
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Filtra por UUID del AgroUnit (productor). Incluye todos los ranchos y lotes del productor.",
        ),
        OpenApiParameter(
            name="datalayer",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Filtra por codigo unico del DataLayer (ej: `SUELO-2024`, `NDVI-DRONE`). Ver GET /api/v1/datalayers/.",
        ),
        OpenApiParameter(
            name="attribute",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=False,
            description=(
                "Filtra puntos que contienen la clave JSONB indicada en `raw_data` "
                "(ej: `?attribute=pH` retorna solo puntos que tienen la clave `pH`). "
                "Util para descartar puntos con datos incompletos antes de renderizar el mapa de calor."
            ),
        ),
    ],
)
class DataLayerPointsListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DataLayerPointsSerializer
    pagination_class = None  # Retorna todos los puntos — el cliente debe filtrar antes de llamar

    def get_queryset(self):
        qs = DataLayerPoints.objects.select_related(
            "header__datalayer", "plot__ranch__producer"
        ).all()
        params = self.request.query_params

        header_id = params.get("header")
        if header_id:
            qs = qs.filter(header_id=header_id)

        plot_id = params.get("plot")
        if plot_id:
            qs = qs.filter(plot_id=plot_id)

        ranch_id = params.get("ranch")
        if ranch_id:
            qs = qs.filter(plot__ranch_id=ranch_id)

        agro_unit_id = params.get("agro_unit")
        if agro_unit_id:
            qs = qs.filter(plot__ranch__producer_id=agro_unit_id)

        datalayer_code = params.get("datalayer")
        if datalayer_code:
            qs = qs.filter(header__datalayer__code=datalayer_code)

        attribute = params.get("attribute")
        if attribute:
            qs = qs.filter(raw_data__has_key=attribute)

        return qs


@extend_schema(tags=["datalayers"], summary="Registrar un punto individual (uso excepcional)")
class DataLayerPointsCreateView(generics.CreateAPIView):
    permission_classes = [IsTechnician]
    queryset = DataLayerPoints.objects.all()
    serializer_class = DataLayerPointsSerializer


@extend_schema(tags=["datalayers"], summary="Detalle de un punto georreferenciado")
class DataLayerPointsDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DataLayerPointsSerializer

    def get_queryset(self):
        return DataLayerPoints.objects.select_related(
            "header__datalayer", "plot"
        )


# ---------------------------------------------------------------------------
# Export — descarga CSV de DataLayerPoints con columnas JSONB aplanadas.
# Acepta los mismos filtros que DataLayerPointsListView.
# ---------------------------------------------------------------------------

@extend_schema(
    tags=["datalayers"],
    summary="Exportar puntos a CSV (descarga)",
    description=(
        "Genera y descarga un archivo CSV con los puntos filtrados. "
        "Las claves del JSONB `raw_data` se aplanan como columnas individuales "
        "(ej: `pH`, `C`, `N`). Acepta los mismos filtros que `GET /api/v1/datalayers/points/`.\n\n"
        "**Nombre del archivo:** `{datalayer}_{plot}_{fecha}.csv`\n\n"
        "**Columnas fijas:** `lat`, `lon`, `captured_at`\n\n"
        "**Columnas dinamicas:** una por cada clave presente en `raw_data` del conjunto filtrado."
    ),
    parameters=[
        OpenApiParameter(name="header",     type=OpenApiTypes.UUID, location=OpenApiParameter.QUERY, required=False),
        OpenApiParameter(name="plot",       type=OpenApiTypes.UUID, location=OpenApiParameter.QUERY, required=False),
        OpenApiParameter(name="ranch",      type=OpenApiTypes.UUID, location=OpenApiParameter.QUERY, required=False),
        OpenApiParameter(name="agro_unit",  type=OpenApiTypes.UUID, location=OpenApiParameter.QUERY, required=False),
        OpenApiParameter(name="datalayer",  type=OpenApiTypes.STR,  location=OpenApiParameter.QUERY, required=False),
        OpenApiParameter(name="attribute",  type=OpenApiTypes.STR,  location=OpenApiParameter.QUERY, required=False),
    ],
    responses={200: OpenApiTypes.BINARY},
)
class DataLayerPointsExportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = DataLayerPoints.objects.select_related(
            "header__datalayer", "plot"
        ).all()
        params = request.query_params

        header_id = params.get("header")
        if header_id:
            qs = qs.filter(header_id=header_id)

        plot_id = params.get("plot")
        if plot_id:
            qs = qs.filter(plot_id=plot_id)

        ranch_id = params.get("ranch")
        if ranch_id:
            qs = qs.filter(plot__ranch_id=ranch_id)

        agro_unit_id = params.get("agro_unit")
        if agro_unit_id:
            qs = qs.filter(plot__ranch__producer_id=agro_unit_id)

        datalayer_code = params.get("datalayer")
        if datalayer_code:
            qs = qs.filter(header__datalayer__code=datalayer_code)

        attribute = params.get("attribute")
        if attribute:
            qs = qs.filter(raw_data__has_key=attribute)

        # Materializar el queryset una sola vez para poder iterar dos veces
        # (una para descubrir las claves JSONB, otra para escribir las filas)
        points = list(qs)

        # Recolectar todas las claves JSONB presentes en el conjunto filtrado,
        # manteniendo orden de insercion (dict preserva orden desde Python 3.7)
        jsonb_keys = list(dict.fromkeys(
            key
            for point in points
            for key in (point.raw_data or {}).keys()
        ))

        # Construir nombre de archivo descriptivo
        dl_code  = datalayer_code or "datalayer"
        plot_obj = points[0].plot if points and points[0].plot else None
        plot_code = plot_obj.code if plot_obj else "sin-plot"
        filename = f"{dl_code}_{plot_code}_{date.today()}.csv"

        # Escribir CSV en memoria (StringIO evita archivos temporales en disco)
        buffer = io.StringIO()
        writer = csv.writer(buffer)

        # Fila de encabezado: columnas fijas + columnas dinamicas del JSONB
        writer.writerow(["lat", "lon", "captured_at"] + jsonb_keys)

        for point in points:
            lon, lat = point.geom.coords  # GeoJSON: coords = (longitude, latitude)
            raw = point.raw_data or {}
            writer.writerow(
                [lat, lon, point.captured_at] + [raw.get(k, "") for k in jsonb_keys]
            )

        buffer.seek(0)
        response = HttpResponse(buffer, content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
