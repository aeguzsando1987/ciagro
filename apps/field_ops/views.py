from rest_framework import generics, permissions
from apps.field_ops.models import CropCatalog, PestCatalog, FieldTask
from apps.field_ops.serializers import CropCatalogSerializer, PestCatalogSerializer, FieldTaskSerializer
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

# Create your views here.
