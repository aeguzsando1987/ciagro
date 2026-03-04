from rest_framework import generics, permissions
from drf_spectacular.utils import extend_schema
from apps.organizations.models import AgroSector, AgroUnit, Contact, ContactAssignment
from apps.organizations.serializers import (
    AgroSectorSerializer,
    AgroUnitSerializer,
    ContactSerializer,
    ContactAssignmentSerializer,
)
from apps.users.permissions import IsSuperAdmin
from apps.core.mixins import SoftDeleteMixin, ScopeFilterMixin


@extend_schema(tags=["organizations"], summary="Listar sectores agricolas")
class AgroSectorListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = AgroSector.objects.all()
    serializer_class = AgroSectorSerializer


@extend_schema(tags=["organizations"], summary="Crear sector agricola")
class AgroSectorCreateView(generics.CreateAPIView):
    permission_classes = [IsSuperAdmin]
    queryset = AgroSector.objects.all()
    serializer_class = AgroSectorSerializer


@extend_schema(tags=["organizations"], summary="Detalle / actualizar / eliminar sector agricola")
class AgroSectorDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsSuperAdmin]
    queryset = AgroSector.objects.all()
    serializer_class = AgroSectorSerializer


@extend_schema(
    tags=["organizations"],
    summary="Listar unidades agricolas (AgroUnit)",
    description=(
        "Retorna las unidades agricolas visibles al usuario. "
        "SuperAdmin ve todas; otros roles ven solo sus unidades asignadas via `UserAssignment`."
    ),
)
class AgroUnitListView(ScopeFilterMixin, generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = AgroUnit.objects.filter(is_deleted=False).select_related("agro_sector", "country", "state").order_by("commercial_name")
    serializer_class = AgroUnitSerializer


@extend_schema(tags=["organizations"], summary="Crear unidad agricola")
class AgroUnitCreateView(generics.CreateAPIView):
    permission_classes = [IsSuperAdmin]
    queryset = AgroUnit.objects.all()
    serializer_class = AgroUnitSerializer


@extend_schema(tags=["organizations"], summary="Detalle de una unidad agricola")
class AgroUnitDetailView(ScopeFilterMixin, generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = AgroUnit.objects.filter(is_deleted=False).select_related("agro_sector", "country", "state").order_by("commercial_name")
    serializer_class = AgroUnitSerializer


@extend_schema(tags=["organizations"], summary="Actualizar unidad agricola")
class AgroUnitUpdateView(generics.UpdateAPIView):
    permission_classes = [IsSuperAdmin]
    queryset = AgroUnit.objects.filter(is_deleted=False)
    serializer_class = AgroUnitSerializer


@extend_schema(tags=["organizations"], summary="Eliminar unidad agricola (soft delete)")
class AgroUnitDestroyView(SoftDeleteMixin, generics.DestroyAPIView):
    permission_classes = [IsSuperAdmin]
    queryset = AgroUnit.objects.filter(is_deleted=False)


@extend_schema(tags=["organizations"], summary="Listar contactos")
class ContactListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Contact.objects.filter(is_deleted=False).order_by("name")
    serializer_class = ContactSerializer


@extend_schema(tags=["organizations"], summary="Crear contacto")
class ContactCreateView(generics.CreateAPIView):
    permission_classes = [IsSuperAdmin]
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer


@extend_schema(tags=["organizations"], summary="Detalle / actualizar / eliminar contacto")
class ContactDetailView(SoftDeleteMixin, generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsSuperAdmin]
    queryset = Contact.objects.filter(is_deleted=False)
    serializer_class = ContactSerializer


@extend_schema(tags=["organizations"], summary="Asignar contacto a unidad agricola")
class ContactAssignmentCreateView(generics.CreateAPIView):
    permission_classes = [IsSuperAdmin]
    queryset = ContactAssignment.objects.all()
    serializer_class = ContactAssignmentSerializer


