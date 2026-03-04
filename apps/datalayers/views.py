# apps/datalayers/views.py
import tempfile
from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework import status as http_status
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
        "Retorna los puntos de captura de muestras agrícolas. Cada punto incluye:\n\n"
        "- `geom`: coordenadas WGS84 (EPSG:4326) — **Point** GeoJSON\n"
        "- `raw_data`: objeto JSONB con los atributos medidos en el punto "
        "(pH, C, N, NDVI, etc.) definidos por el `definition_scheme` del DataLayer asociado\n\n"
        "**Uso típico para mapas de calor**: filtrar por `header` y usar `geom` + "
        "el atributo deseado de `raw_data` como valor de intensidad en el visor geoespacial.\n\n"
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
            description="Filtra puntos por UUID del DataLayerHeader (sesión de captura).",
        ),
    ],
)
class DataLayerPointsListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DataLayerPointsSerializer

    def get_queryset(self):
        # select_related evita N+1 al acceder a header.datalayer en validate()
        qs = DataLayerPoints.objects.select_related(
            "header__datalayer", "plot"
        ).all()
        header_id = self.request.query_params.get("header")
        if header_id:
            qs = qs.filter(header_id=header_id)
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
