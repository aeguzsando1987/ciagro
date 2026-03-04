from rest_framework import generics, permissions
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from apps.geo_assets.models import Ranch, Plot, RanchPartner
from apps.geo_assets.serializers import RanchSerializer, PlotSerializer, RanchPartnerSerializer
from apps.users.permissions import IsSuperAdmin
from apps.core.mixins import SoftDeleteMixin, ScopeFilterMixin


@extend_schema(
    tags=["geo-assets"],
    summary="Listar ranchos (GeoJSON FeatureCollection)",
    description=(
        "Retorna los ranchos accesibles al usuario autenticado como GeoJSON `FeatureCollection`. "
        "Cada `Feature` incluye el polígono o punto de ubicación en `geometry` y los campos del rancho en `properties`. "
        "SuperAdmin ve todos; otros roles ven solo los ranchos de sus unidades asignadas."
    ),
)
class RanchListView(ScopeFilterMixin, generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = RanchSerializer

    def get_queryset(self):
        qs = Ranch.objects.filter(is_deleted=False).select_related("producer", "country", "state")
        if self.is_super_admin():
            return qs
        return qs.filter(producer_id__in=self.get_assigned_units_ids())


@extend_schema(tags=["geo-assets"], summary="Crear rancho")
class RanchCreateView(generics.CreateAPIView):
    permission_classes = [IsSuperAdmin]
    queryset = Ranch.objects.all()
    serializer_class = RanchSerializer


@extend_schema(tags=["geo-assets"], summary="Detalle de un rancho (GeoJSON Feature)")
class RanchDetailView(ScopeFilterMixin, generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = RanchSerializer

    def get_queryset(self):
        qs = Ranch.objects.filter(is_deleted=False).select_related("producer", "country", "state")
        if self.is_super_admin():
            return qs
        return qs.filter(producer_id__in=self.get_assigned_units_ids())


@extend_schema(tags=["geo-assets"], summary="Actualizar rancho")
class RanchUpdateView(generics.UpdateAPIView):
    permission_classes = [IsSuperAdmin]
    queryset = Ranch.objects.filter(is_deleted=False)
    serializer_class = RanchSerializer


@extend_schema(tags=["geo-assets"], summary="Eliminar rancho (soft delete)")
class RanchDestroyView(SoftDeleteMixin, generics.DestroyAPIView):
    permission_classes = [IsSuperAdmin]
    queryset = Ranch.objects.filter(is_deleted=False)


@extend_schema(
    tags=["geo-assets"],
    summary="Listar parcelas (GeoJSON FeatureCollection)",
    description=(
        "Retorna las parcelas accesibles al usuario como GeoJSON `FeatureCollection`. "
        "Cada `Feature` incluye el polígono de la parcela en `geometry` y sus atributos en `properties`. "
        "Las parcelas son la unidad espacial de referencia para los `DataLayerPoints` (mapas de calor)."
    ),
)
class PlotListView(ScopeFilterMixin, generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PlotSerializer

    def get_queryset(self):
        qs = Plot.objects.filter(is_deleted=False).select_related("ranch__producer")
        if self.is_super_admin():
            return qs
        return qs.filter(ranch__producer_id__in=self.get_assigned_units_ids())


@extend_schema(tags=["geo-assets"], summary="Crear parcela")
class PlotCreateView(generics.CreateAPIView):
    permission_classes = [IsSuperAdmin]
    queryset = Plot.objects.all()
    serializer_class = PlotSerializer


@extend_schema(tags=["geo-assets"], summary="Detalle de una parcela (GeoJSON Feature)")
class PlotDetailView(ScopeFilterMixin, generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PlotSerializer

    def get_queryset(self):
        qs = Plot.objects.filter(is_deleted=False).select_related("ranch__producer")
        if self.is_super_admin():
            return qs
        return qs.filter(ranch__producer_id__in=self.get_assigned_units_ids())


@extend_schema(tags=["geo-assets"], summary="Actualizar parcela")
class PlotUpdateView(generics.UpdateAPIView):
    permission_classes = [IsSuperAdmin]
    queryset = Plot.objects.filter(is_deleted=False)
    serializer_class = PlotSerializer


@extend_schema(tags=["geo-assets"], summary="Eliminar parcela (soft delete)")
class PlotDestroyView(SoftDeleteMixin, generics.DestroyAPIView):
    permission_classes = [IsSuperAdmin]
    queryset = Plot.objects.filter(is_deleted=False)


@extend_schema(
    tags=["geo-assets"],
    summary="Listar socios del rancho",
    parameters=[
        OpenApiParameter(
            name="ranch",
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Filtra socios por UUID del rancho.",
        ),
    ],
)
class RanchPartnerListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = RanchPartnerSerializer

    def get_queryset(self):
        qs = RanchPartner.objects.select_related("ranch", "partner").order_by("id")
        ranch_id = self.request.query_params.get("ranch")
        if ranch_id:
            qs = qs.filter(ranch_id=ranch_id)
        return qs


@extend_schema(tags=["geo-assets"], summary="Asociar socio a rancho")
class RanchPartnerCreateView(generics.CreateAPIView):
    permission_classes = [IsSuperAdmin]
    queryset = RanchPartner.objects.all()
    serializer_class = RanchPartnerSerializer


@extend_schema(tags=["geo-assets"], summary="Eliminar asociación rancho-socio")
class RanchPartnerDestroyView(generics.DestroyAPIView):
    permission_classes = [IsSuperAdmin]
    queryset = RanchPartner.objects.all()
