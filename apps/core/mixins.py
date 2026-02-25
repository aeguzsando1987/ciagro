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