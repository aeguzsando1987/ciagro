from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from apps.geo_assets.models import Ranch, Plot, RanchPartner

class RanchSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = Ranch
        geo_field = "geom"
        fields = [
            "id", "code", "name", "producer",
            "address_line_1", "address_line_2",
            "location_url", "lat", "lon", "geom",
            "country", "state", "city", "area_uom",
            "total_area", "status", "slug",
        ]
        read_only_fields = ["id", "slug"]

    def validate(self, data):
        country = data.get("country") or (self.instance.country if self.instance else None)
        state = data.get("state")
        if state and country and state.country_id != country.id:
            raise serializers.ValidationError(
                {"state": "El estado no pertenece al país seleccionado."}
            )
        return data
        

class PlotSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = Plot
        geo_field = "geom"
        fields = [
            "id", "code", "description", "ranch",
            "geom", "centroid", "total_area", 
            "tech_spraying", "comments", "status", 
            "slug",
        ]
        read_only_fields = ["id", "slug"]
        


class RanchPartnerSerializer(serializers.ModelSerializer):

    RELATION_TO_UNIT_TYPE = {
        "guild": "Asociación agrícola",
        "grain_collector": "Acopiadora de grano",
        "lab": "Laboratorio",
    }

    class Meta:
        model = RanchPartner
        fields = [
            "id", "ranch",
            "partner",
            "relation_type",
        ]

    def validate(self, attrs):
        partner = attrs.get("partner")
        relation_type = attrs.get("relation_type")
        expected_type = self.RELATION_TO_UNIT_TYPE.get(relation_type)
        if expected_type and partner.unit_type != expected_type:
            raise serializers.ValidationError(
                {"partner": f"Esta relación requiere un socio de tipo '{expected_type}'."}
            )
        return attrs