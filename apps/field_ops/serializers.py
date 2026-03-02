from rest_framework import serializers
from apps.field_ops.models import CropCatalog, PestCatalog, FieldTask
from apps.datalayers.models import DataLayer

class CropCatalogSerializer(serializers.ModelSerializer):
    class Meta:
        model = CropCatalog
        fields = ["id", "name", "description", "photo_url", 
                "additional_params", "attachments_url"]
        read_only_fields = ["id"]
        

class PestCatalogSerializer(serializers.ModelSerializer):
    default_crop = CropCatalogSerializer(read_only=True)
    default_crop_id = serializers.PrimaryKeyRelatedField(
        queryset=CropCatalog.objects.all(), 
        source="default_crop", 
        write_only=True, 
        required=False, 
        allow_null=True
    )
    
    class Meta:
        model = PestCatalog
        fields = ["id", "name", "default_crop", "default_crop_id", 
                "description", "photo_url", "ref_value",
                "additional_params", "attachments_url",]
        read_only_fields = ["id"]
        
        
class FieldTaskSerializer(serializers.ModelSerializer):
    crop = CropCatalogSerializer(read_only=True)
    datalayer_code = serializers.CharField(source="datalayer.code", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    
    crop_id = serializers.PrimaryKeyRelatedField(
        queryset=CropCatalog.objects.all(), 
        source="crop", 
        write_only=True, 
        required=False, 
        allow_null=True
    )
    datalayer_id = serializers.PrimaryKeyRelatedField(
        queryset=DataLayer.objects.all(),
        source="datalayer",
        write_only=True,
        required=False,
        allow_null=True
    )
    class Meta:
        model = FieldTask
        fields = ["id", "voucher_code",
                "title", "cycle",
                "status", "status_display",
                "crop", "crop_id",
                "datalayer_code", "datalayer_id",
                "individual", "agro_unit",
                "plot", "parent_task",
                "est_start_date", "est_finish_date",
                "actual_start_date", "actual_finish_date",
                "location_url", "attachments_url",]
        read_only_fields = ["id", "status_display", "datalayer_code"]
        


