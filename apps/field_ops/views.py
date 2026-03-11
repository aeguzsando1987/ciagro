from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status as http_status
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from apps.field_ops.models import CropCatalog, PestCatalog, FieldTask, FieldTaskReport
from apps.field_ops.serializers import (
    CropCatalogSerializer, PestCatalogSerializer,
    FieldTaskSerializer, FieldTaskReportSerializer,
)
from apps.users.permissions import IsSuperAdmin
from apps.core.mixins import ScopeFilterMixin


@extend_schema(tags=["field-ops"], summary="Listar catálogo de cultivos")
class CropCatalogListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = CropCatalog.objects.all()
    serializer_class = CropCatalogSerializer


@extend_schema(tags=["field-ops"], summary="Crear variedad de cultivo")
class CropCatalogCreateView(generics.CreateAPIView):
    permission_classes = [IsSuperAdmin]
    queryset = CropCatalog.objects.all()
    serializer_class = CropCatalogSerializer


@extend_schema(tags=["field-ops"], summary="Detalle de un cultivo")
class CropCatalogDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = CropCatalog.objects.all()
    serializer_class = CropCatalogSerializer


@extend_schema(tags=["field-ops"], summary="Actualizar cultivo")
class CropCatalogUpdateView(generics.UpdateAPIView):
    permission_classes = [IsSuperAdmin]
    queryset = CropCatalog.objects.all()
    serializer_class = CropCatalogSerializer


@extend_schema(
    tags=["field-ops"],
    summary="Listar catálogo de plagas",
    parameters=[
        OpenApiParameter(
            name="default_crop",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Filtra plagas por ID del cultivo asociado.",
        ),
    ],
)
class PestCatalogListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PestCatalogSerializer

    def get_queryset(self):
        qs = PestCatalog.objects.select_related("default_crop")
        crop_id = self.request.query_params.get("default_crop")
        if crop_id:
            qs = qs.filter(default_crop_id=crop_id)
        return qs


@extend_schema(tags=["field-ops"], summary="Crear plaga")
class PestCatalogCreateView(generics.CreateAPIView):
    permission_classes = [IsSuperAdmin]
    queryset = PestCatalog.objects.all()
    serializer_class = PestCatalogSerializer


@extend_schema(tags=["field-ops"], summary="Detalle de una plaga")
class PestCatalogDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = PestCatalog.objects.select_related("default_crop")
    serializer_class = PestCatalogSerializer


@extend_schema(tags=["field-ops"], summary="Actualizar plaga")
class PestCatalogUpdateView(generics.UpdateAPIView):
    permission_classes = [IsSuperAdmin]
    queryset = PestCatalog.objects.all()
    serializer_class = PestCatalogSerializer


@extend_schema(
    tags=["field-ops"],
    summary="Listar tareas de campo",
    parameters=[
        OpenApiParameter(
            name="status",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Filtra por estado: `open`, `in_progress`, `closed`.",
            enum=["open", "in_progress", "closed"],
        ),
    ],
)
class FieldTaskListView(ScopeFilterMixin, generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class   = FieldTaskSerializer

    def get_queryset(self):
        qs = FieldTask.objects.select_related(
            "datalayer", "individual", "agro_unit", "plot", "crop"
        )
        if not self.is_super_admin():
            qs = qs.filter(agro_unit__in=self.get_assigned_units_ids())
        status = self.request.query_params.get("status")
        if status:
            qs = qs.filter(status=status)
        return qs


@extend_schema(tags=["field-ops"], summary="Crear tarea de campo")
class FieldTaskCreateView(generics.CreateAPIView):
    permission_classes = [IsSuperAdmin]
    queryset           = FieldTask.objects.all()
    serializer_class   = FieldTaskSerializer


@extend_schema(tags=["field-ops"], summary="Detalle de una tarea de campo")
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


@extend_schema(tags=["field-ops"], summary="Actualizar tarea de campo")
class FieldTaskUpdateView(generics.UpdateAPIView):
    permission_classes = [IsSuperAdmin]
    queryset           = FieldTask.objects.all()
    serializer_class   = FieldTaskSerializer


@extend_schema(
    tags=["field-ops"],
    summary="Generar reporte de tarea (idempotente)",
    description=(
        "Genera (o regenera) el `FieldTaskReport` de una `FieldTask`. "
        "Agrega estadísticas numéricas (`min`, `max`, `avg`, `count`) de cada atributo "
        "JSONB presente en los `DataLayerPoints` asociados a la tarea.\n\n"
        "**Idempotente**: si el reporte ya existe, actualiza `summary_data` y el evaluador; "
        "los campos manuales (`conclusion`, etc.) no se sobreescriben.\n\n"
        "**409 Conflict** si la tarea está en estado `closed`."
    ),
    responses={
        200: FieldTaskReportSerializer,
        201: FieldTaskReportSerializer,
        404: OpenApiTypes.OBJECT,
        409: OpenApiTypes.OBJECT,
    },
)
class GenerateReportView(ScopeFilterMixin, APIView):
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
        """Agrega estadísticas numéricas de parameters de todos los puntos de la tarea."""
        from apps.datalayers.models import DataLayerHeader, DataLayerPoints

        header_ids = DataLayerHeader.objects.filter(task=task).values_list("id", flat=True)
        parameters_qs = DataLayerPoints.objects.filter(
            header_id__in=header_ids
        ).values_list("parameters", flat=True)

        total = 0
        field_values: dict = {}
        for parameters in parameters_qs:
            total += 1
            for key, val in parameters.items():
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
