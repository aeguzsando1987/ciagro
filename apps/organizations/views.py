from rest_framework import generics, permissions
from apps.organizations.models import AgroSector, AgroUnit
from apps.organizations.serializers import AgroSectorSerializer, AgroUnitSerializer
from apps.users.permissions import IsSuperAdmin
from apps.core.mixins import SoftDeleteMixin

class AgroSectorListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = AgroSector.objects.all()
    serializer_class = AgroSectorSerializer
    

class AgroSectorCreateView(generics.CreateAPIView):
    permission_classes = [IsSuperAdmin]
    queryset = AgroSector.objects.all()
    serializer_class = AgroSectorSerializer
    

class AgroSectorDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsSuperAdmin]
    queryset = AgroSector.objects.all()
    serializer_class = AgroSectorSerializer
    

class AgroUnitListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = AgroUnit.objects.filter(is_deleted=False).select_related("agro_sector", "country", "state").order_by("commercial_name")
    serializer_class = AgroUnitSerializer
    
    
class AgroUnitCreateView(generics.CreateAPIView):
    permission_classes = [IsSuperAdmin]
    queryset = AgroUnit.objects.all()
    serializer_class = AgroUnitSerializer


class AgroUnitDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = AgroUnit.objects.filter(is_deleted=False).select_related("agro_sector", "country", "state").order_by("commercial_name")
    serializer_class = AgroUnitSerializer
    

class AgroUnitUpdateView(generics.UpdateAPIView):
    permission_classes = [IsSuperAdmin]
    queryset = AgroUnit.objects.filter(is_deleted=False)
    serializer_class = AgroUnitSerializer
    

class AgroUnitDestroyView(SoftDeleteMixin, generics.DestroyAPIView):
    permission_classes = [IsSuperAdmin]
    queryset = AgroUnit.objects.filter(is_deleted=False)



