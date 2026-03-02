from rest_framework import generics, permissions
from apps.datalayers.models import DataLayer
from apps.datalayers.serializers import DataLayerSerializer
from apps.users.permissions import IsSuperAdmin


class DataLayerListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = DataLayer.objects.all()
    serializer_class = DataLayerSerializer
    

class DataLayerCreateView(generics.CreateAPIView):
    permission_classes = [IsSuperAdmin] # Asi podran usuarios no superadmin pero calificados crear DataLayer????
    queryset = DataLayer.objects.all()
    serializer_class = DataLayerSerializer
    
    
class DataLayerDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = DataLayer.objects.all()
    serializer_class = DataLayerSerializer
    

class DataLayerUpdateView(generics.UpdateAPIView):
    permission_classes = [IsSuperAdmin] # Asi podran usuarios no superadmin pero calificados modificar DataLayer????
    queryset = DataLayer.objects.all()
    serializer_class = DataLayerSerializer

# Create your views here.
