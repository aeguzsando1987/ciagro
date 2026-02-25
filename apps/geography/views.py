from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from apps.geography.models import Country, State
from apps.geography.serializers import CountrySerializer, StateDetailSerializer

class CountryListView(generics.ListAPIView):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    permission_classes = [IsAuthenticated]
    
class StateListView(generics.ListAPIView):
    serializer_class = StateDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = State.objects.select_related("country")
        country_iso2 = self.request.query_params.get("country")
        if country_iso2:
            queryset = queryset.filter(country__iso_2=country_iso2.upper())
        return queryset
