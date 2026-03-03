# apps/datalayers/views.py
import tempfile
from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework import status as http_status
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

class DataLayerListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = DataLayer.objects.all()
    serializer_class = DataLayerSerializer


class DataLayerCreateView(generics.CreateAPIView):
    permission_classes = [IsSuperAdmin]
    queryset = DataLayer.objects.all()
    serializer_class = DataLayerSerializer


class DataLayerDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = DataLayer.objects.all()
    serializer_class = DataLayerSerializer


class DataLayerUpdateView(generics.UpdateAPIView):
    permission_classes = [IsSuperAdmin]
    queryset = DataLayer.objects.all()
    serializer_class = DataLayerSerializer


# ---------------------------------------------------------------------------
# DataLayerHeader — encabezado de sesión de captura.
# Los técnicos crean y el supervisor puede corregir metadatos.
# ---------------------------------------------------------------------------

class DataLayerHeaderListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DataLayerHeaderSerializer

    def get_queryset(self):
        return DataLayerHeader.objects.select_related(
            "datalayer", "plot", "crop", "task"
        ).all()


class DataLayerHeaderCreateView(generics.CreateAPIView):
    permission_classes = [IsTechnician]
    queryset = DataLayerHeader.objects.all()
    serializer_class = DataLayerHeaderSerializer


class DataLayerHeaderDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DataLayerHeaderSerializer

    def get_queryset(self):
        return DataLayerHeader.objects.select_related(
            "datalayer", "plot", "crop", "task"
        ).all()


class DataLayerHeaderUpdateView(generics.UpdateAPIView):
    permission_classes = [IsSupervisor]
    queryset = DataLayerHeader.objects.all()
    serializer_class = DataLayerHeaderSerializer


class DataLayerHeaderImportView(APIView):
    """
    POST /api/v1/datalayers/headers/import/

    Crea un DataLayerHeader y encola una tarea Celery que procesa el CSV
    y crea los DataLayerPoints en bulk (sin bloquear el HTTP request).

    Body (multipart/form-data):
        - task         UUID, opcional  — tarea de campo que origina la importación
        - datalayer    int, requerido  — contrato de datos a aplicar
        - crop         int, requerido  — cultivo del momento de captura
        - import_date  date, requerido — fecha de la importación
        - csv_file     file, requerido — CSV con columnas: lat, lon, captured_at (opt), + raw_data

    Responde 202 Accepted con { header_id, celery_task_id }
    """
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


class DataLayerPointsCreateView(generics.CreateAPIView):
    permission_classes = [IsTechnician]
    queryset = DataLayerPoints.objects.all()
    serializer_class = DataLayerPointsSerializer


class DataLayerPointsDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DataLayerPointsSerializer

    def get_queryset(self):
        return DataLayerPoints.objects.select_related(
            "header__datalayer", "plot"
        )
