from django.contrib.contenttypes.models import ContentType
from drf_spectacular.utils import OpenApiParameter, extend_schema
from drf_spectacular.types import OpenApiTypes
from rest_framework import generics, permissions
from rest_framework.parsers import FormParser, MultiPartParser

from apps.core.models import Attachment
from apps.core.serializers import AttachmentSerializer
from apps.users.permissions import IsTechnician


@extend_schema(
    tags=["core"],
    summary="Listar / subir archivos adjuntos",
    description=(
        "**GET:** Lista los adjuntos. Filtrar con `?model_name=ranch&object_id=<uuid>` "
        "para obtener los adjuntos de un objeto específico.\n\n"
        "**POST:** Sube un archivo (multipart/form-data). "
        "Requiere nivel mínimo `Technician`. "
        "Actualiza automáticamente `attachments_url` en el objeto padre."
    ),
    parameters=[
        OpenApiParameter(
            name="model_name",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Nombre del modelo en minúsculas (ranch, plot, agrounit, fieldtask, …)",
        ),
        OpenApiParameter(
            name="object_id",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=False,
            description="PK del objeto destino (UUID o entero como string)",
        ),
    ],
)
class AttachmentListCreateView(generics.ListCreateAPIView):
    serializer_class = AttachmentSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsTechnician()]
        return [permissions.IsAuthenticated()]

    def get_parsers(self):
        if getattr(self, "request", None) and self.request.method == "POST":
            return [MultiPartParser(), FormParser()]
        return super().get_parsers()

    def get_queryset(self):
        qs = Attachment.objects.select_related(
            "content_type", "uploaded_by"
        ).order_by("-uploaded_at")
        params = self.request.query_params
        model_name = params.get("model_name")
        object_id  = params.get("object_id")
        if model_name:
            try:
                ct = ContentType.objects.get(model=model_name.lower())
                qs = qs.filter(content_type=ct)
            except ContentType.DoesNotExist:
                return Attachment.objects.none()
        if object_id:
            qs = qs.filter(object_id=object_id)
        return qs


@extend_schema(
    tags=["core"],
    summary="Borrar archivo adjunto",
    description=(
        "Elimina el registro `Attachment` y actualiza automáticamente "
        "`attachments_url` en el objeto padre. "
        "Requiere nivel mínimo `Technician`."
    ),
)
class AttachmentDestroyView(generics.DestroyAPIView):
    permission_classes = [IsTechnician]
    queryset = Attachment.objects.all()
