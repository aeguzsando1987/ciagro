from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from apps.geography.models import Country, State
from apps.geography.serializers import CountrySerializer, StateDetailSerializer


@extend_schema(tags=["geography"], summary="Listar paises")
class CountryListView(generics.ListAPIView):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    permission_classes = [IsAuthenticated]


@extend_schema(
    tags=["geography"],
    summary="Listar estados/provincias",
    parameters=[
        OpenApiParameter(
            name="country",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Filtra por codigo ISO-2 del pais (ej: `MX`, `US`).",
        ),
    ],
)
class StateListView(generics.ListAPIView):
    serializer_class = StateDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = State.objects.select_related("country")
        country_iso2 = self.request.query_params.get("country")
        if country_iso2:
            queryset = queryset.filter(country__iso_2=country_iso2.upper())
        return queryset
