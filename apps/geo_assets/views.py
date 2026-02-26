from rest_framework import generics, permissions
from apps.geo_assets.models import Ranch, Plot, RanchPartner
from apps.geo_assets.serializers import RanchSerializer, PlotSerializer, RanchPartnerSerializer
from apps.users.permissions import IsSuperAdmin
from apps.core.mixins import SoftDeleteMixin, ScopeFilterMixin


class RanchListView(ScopeFilterMixin, generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = RanchSerializer

    def get_queryset(self):
        qs = Ranch.objects.filter(is_deleted=False).select_related("producer", "country", "state")
        if self.is_super_admin():
            return qs
        return qs.filter(producer_id__in=self.get_assigned_units_ids())


class RanchCreateView(generics.CreateAPIView):
    permission_classes = [IsSuperAdmin]
    queryset = Ranch.objects.all()
    serializer_class = RanchSerializer


class RanchDetailView(ScopeFilterMixin, generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = RanchSerializer

    def get_queryset(self):
        qs = Ranch.objects.filter(is_deleted=False).select_related("producer", "country", "state")
        if self.is_super_admin():
            return qs
        return qs.filter(producer_id__in=self.get_assigned_units_ids())


class RanchUpdateView(generics.UpdateAPIView):
    permission_classes = [IsSuperAdmin]
    queryset = Ranch.objects.filter(is_deleted=False)
    serializer_class = RanchSerializer


class RanchDestroyView(SoftDeleteMixin, generics.DestroyAPIView):
    permission_classes = [IsSuperAdmin]
    queryset = Ranch.objects.filter(is_deleted=False)


class PlotListView(ScopeFilterMixin, generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PlotSerializer

    def get_queryset(self):
        qs = Plot.objects.filter(is_deleted=False).select_related("ranch__producer")
        if self.is_super_admin():
            return qs
        return qs.filter(ranch__producer_id__in=self.get_assigned_units_ids())


class PlotCreateView(generics.CreateAPIView):
    permission_classes = [IsSuperAdmin]
    queryset = Plot.objects.all()
    serializer_class = PlotSerializer


class PlotDetailView(ScopeFilterMixin, generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PlotSerializer
    
    def get_queryset(self):
        qs = Plot.objects.filter(is_deleted=False).select_related("ranch__producer")
        if self.is_super_admin():
            return qs
        return qs.filter(ranch__producer_id__in=self.get_assigned_units_ids())


class PlotUpdateView(generics.UpdateAPIView):
    permission_classes = [IsSuperAdmin] # Se define que usuario puede actualizar
    queryset = Plot.objects.filter(is_deleted=False) # Se define el queryset (esto es como una consulta a la BD con filtro)
    serializer_class = PlotSerializer # Se define el serializer para que se serialice el objeto y se envie en la respuesta


class PlotDestroyView(SoftDeleteMixin, generics.DestroyAPIView):
    permission_classes = [IsSuperAdmin]
    queryset = Plot.objects.filter(is_deleted=False)
    # Aqui no se ocupa serializer porque se usa el SoftDeleteMixin para desactivar.
    

class RanchPartnerListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = RanchPartnerSerializer
    
    def get_queryset(self):
        qs = RanchPartner.objects.select_related("ranch", "partner").order_by("id") # se define el queryset (se seleccionan los datos relacionados a ranch y partner)
        ranch_id = self.request.query_params.get("ranch")
        if ranch_id:
            qs = qs.filter(ranch_id=ranch_id)
        return qs


class RanchPartnerCreateView(generics.CreateAPIView):
    permission_classes = [IsSuperAdmin]
    queryset = RanchPartner.objects.all()
    serializer_class = RanchPartnerSerializer


class RanchPartnerDestroyView(generics.DestroyAPIView):
    permission_classes = [IsSuperAdmin]
    queryset = RanchPartner.objects.all()
