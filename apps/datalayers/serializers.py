from rest_framework import serializers
from rest_framework_gis.serializers import GeoModelSerializer
from apps.datalayers.models import DataLayer, DataLayerHeader, DataLayerPoints
from apps.datalayers.validators import validate_raw_data_against_scheme

class DataLayerSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = DataLayer
        fields = [
            "id", "name",
            "code", "definition_scheme",
            "evaluation_scheme", "attachments_url",
            "description", "created_at"
        ]
        read_only_fields = ["created_at"]
        
        
class DataLayerHeaderSerializer(serializers.ModelSerializer):
    datalayer_code = serializers.CharField(source="datalayer.code", read_only=True)
    plot_code = serializers.CharField(source="plot.code", read_only=True, allow_null=True)
    points_count = serializers.SerializerMethodField()
    
    class Meta:
        model = DataLayerHeader
        fields = [
            "id", "task", "plot",
            "plot_code", "crop", "datalayer", 
            "datalayer_code", "import_date", "points_count",
            "created_at"
        ]
        read_only_fields = ["id", "plot", "plot_code", "created_at"]
        # plot es read_only porque se hereda automático de task.plot en save() (denormalizado)
        
    def get_points_count(self, obj):
        return obj.points.count()
    

class DataLayerPointsSerializer(GeoModelSerializer):
    class Meta:
        model = DataLayerPoints
        geo_field = "geom"
        fields = ["id", "header", "plot", "geom", "captured_at", "raw_data"]
        read_only_fields = ["id", "plot"]
        # plot es read_only porque se hereda automático de header.plot en save() (denormalizado)

    def validate(self, data):
        header = data.get("header")
        raw_data = data.get("raw_data", {})
        if header:
            scheme = header.datalayer.definition_scheme
            validate_raw_data_against_scheme(raw_data, scheme)
        return data