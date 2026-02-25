from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

class SoftDeleteMixin:
    """
    Mixin reutilizables para viewsets y GenerricAPIViews
    Sobreescritura de destroy parar desactivar en lugar de eliminar
    Para poder hacer un soft delete se necesitan campos:
    is_deleted
    deleted_at
    deleted_by
    """

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_deleted = True
        instance.deleted_at = timezone.now()
        instance.deleted_by = request.user
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ScopeFilterMixin:
    """
    Para delimitar el alcance del usuario (filtra queryset).
    SuperAdmin (con level >= 5) puede ver todo.
    Otros roles solo pueden ver las agrounidades asignadas (ver UserAssignment - assignments).

    Para vistas de AgroUnit: get_queryset() se filtra por id__in.
    Para vistas dependientes (Ranchos, Parcelas): sobreescribe get_queryset()
    y usa self.get_assigned_units_ids() para generar el filtro propio.
    """

    def get_assigned_units_ids(self):
        return self.request.user.assignments.values_list('agro_unit_id', flat=True)

    def is_super_admin(self):
        user = self.request.user
        return user.user_role is not None and user.user_role.level >= 5

    def get_queryset(self):
        qs = super().get_queryset()
        if self.is_super_admin():
            return qs
        return qs.filter(id__in=self.get_assigned_units_ids())
            