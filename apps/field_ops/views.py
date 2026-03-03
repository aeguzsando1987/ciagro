from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status as http_status
from apps.field_ops.models import CropCatalog, PestCatalog, FieldTask, FieldTaskReport
from apps.field_ops.serializers import (
    CropCatalogSerializer, PestCatalogSerializer,
    FieldTaskSerializer, FieldTaskReportSerializer,
)
from apps.users.permissions import IsSuperAdmin
from apps.core.mixins import ScopeFilterMixin


class CropCatalogListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = CropCatalog.objects.all()
    serializer_class = CropCatalogSerializer


class CropCatalogCreateView(generics.CreateAPIView):
    permission_classes = [IsSuperAdmin]
    queryset = CropCatalog.objects.all()
    serializer_class = CropCatalogSerializer


class CropCatalogDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = CropCatalog.objects.all()
    serializer_class = CropCatalogSerializer


class CropCatalogUpdateView(generics.UpdateAPIView):
    permission_classes = [IsSuperAdmin]
    queryset = CropCatalog.objects.all()
    serializer_class = CropCatalogSerializer


class PestCatalogListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PestCatalogSerializer

    def get_queryset(self):
        qs = PestCatalog.objects.select_related("default_crop")
        crop_id = self.request.query_params.get("default_crop")
        if crop_id:
            qs = qs.filter(default_crop_id=crop_id)
        return qs


class PestCatalogCreateView(generics.CreateAPIView):
    permission_classes = [IsSuperAdmin]
    queryset = PestCatalog.objects.all()
    serializer_class = PestCatalogSerializer


class PestCatalogDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = PestCatalog.objects.select_related("default_crop")
    serializer_class = PestCatalogSerializer


class PestCatalogUpdateView(generics.UpdateAPIView):
    permission_classes = [IsSuperAdmin]
    queryset = PestCatalog.objects.all()
    serializer_class = PestCatalogSerializer

class FieldTaskListView(ScopeFilterMixin, generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class   = FieldTaskSerializer

    def get_queryset(self):
        qs = FieldTask.objects.select_related(
            "datalayer", "individual", "agro_unit", "plot", "crop"
        )
        # Scope: solo tareas de las unidades asignadas al usuario
        if not self.is_super_admin():
            qs = qs.filter(agro_unit__in=self.get_assigned_units_ids())
        # Filtro opcional por status
        status = self.request.query_params.get("status")
        if status:
            qs = qs.filter(status=status)
        return qs


class FieldTaskCreateView(generics.CreateAPIView):
    permission_classes = [IsSuperAdmin]
    queryset           = FieldTask.objects.all()
    serializer_class   = FieldTaskSerializer


class FieldTaskDetailView(ScopeFilterMixin, generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class   = FieldTaskSerializer

    def get_queryset(self):
        qs = FieldTask.objects.select_related(
            "datalayer", "individual", "agro_unit", "plot", "crop"
        )
        if not self.is_super_admin():
            qs = qs.filter(agro_unit__in=self.get_assigned_units_ids())
        return qs


class FieldTaskUpdateView(generics.UpdateAPIView):
    permission_classes = [IsSuperAdmin]
    queryset           = FieldTask.objects.all()
    serializer_class   = FieldTaskSerializer


class GenerateReportView(ScopeFilterMixin, APIView):
    """
    POST /api/v1/field-ops/tasks/<uuid:pk>/generate-report/

    Genera (o regenera) el FieldTaskReport de una FieldTask.

    - Calcula summary_data a partir de todos los DataLayerPoints
      asociados a los DataLayerHeaders de la tarea.
    - Idempotente: si ya existe un reporte para la tarea, lo actualiza
      (summary_data + evaluador). Los campos manuales (conclusion, etc.)
      no se sobreescriben.
    - Bloquea tareas en estado "closed" (409).
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        # 1. Resolver tarea respetando scope de unidades asignadas
        qs = FieldTask.objects.select_related("plot")
        if not self.is_super_admin():
            qs = qs.filter(agro_unit__in=self.get_assigned_units_ids())
        try:
            task = qs.get(pk=pk)
        except FieldTask.DoesNotExist:
            return Response(
                {"detail": "Tarea no encontrada."},
                status=http_status.HTTP_404_NOT_FOUND,
            )

        if task.status == FieldTask.STATUS_CLOSED:
            return Response(
                {"detail": "No se puede generar el reporte de una tarea cerrada."},
                status=http_status.HTTP_409_CONFLICT,
            )

        # 2. Calcular summary_data
        summary_data = self._build_summary(task)

        # 3. Identificar al evaluador (usuario logueado)
        from apps.users.models import Individual
        evaluator = Individual.objects.filter(user=request.user).first()

        # 4. Upsert idempotente — solo se actualizan los campos calculados
        report, created = FieldTaskReport.objects.update_or_create(
            task=task,
            defaults={
                "plot": task.plot,
                "evaluator": evaluator,
                "summary_data": summary_data,
            },
        )

        return Response(
            FieldTaskReportSerializer(report).data,
            status=http_status.HTTP_201_CREATED if created else http_status.HTTP_200_OK,
        )

    def _build_summary(self, task):
        """Agrega estadísticas numéricas de raw_data de todos los puntos de la tarea."""
        from apps.datalayers.models import DataLayerHeader, DataLayerPoints

        header_ids = DataLayerHeader.objects.filter(task=task).values_list("id", flat=True)
        raw_data_qs = DataLayerPoints.objects.filter(
            header_id__in=header_ids
        ).values_list("raw_data", flat=True)

        total = 0
        field_values: dict = {}
        for raw_data in raw_data_qs:
            total += 1
            for key, val in raw_data.items():
                try:
                    field_values.setdefault(key, []).append(float(val))
                except (TypeError, ValueError):
                    pass

        stats = {}
        for field, values in field_values.items():
            n = len(values)
            stats[field] = {
                "count": n,
                "min": round(min(values), 4),
                "max": round(max(values), 4),
                "avg": round(sum(values) / n, 4),
            }

        return {"total_points": total, "fields": stats}
