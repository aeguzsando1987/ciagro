from rest_framework import serializers
from apps.organizations.models import AgroSector, AgroUnit

class AgroSectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgroSector
        fields = ["id", "sector_name", "scian_code", "activity_name", "description"]
        

class AgroUnitSerializer(serializers.ModelSerializer):
    agro_sector = AgroSectorSerializer(read_only=True)
    agro_sector_id = serializers.PrimaryKeyRelatedField(
        queryset=AgroSector.objects.all(),
        source="agro_sector",
        write_only=True,
        required=False,
        allow_null=True
    )
    class Meta:
        model = AgroUnit
        fields = [
            "id", "code", "commercial_name", "company_name",
            "unit_type", "agro_sector", "agro_sector_id",
            "tax_id", "tax_type", "headcount", 
            "phone", "email", "website",
            "address_line_1", "address_line_2", "location_url",
            "country", "state", 
            "status", "additional_params", "attachments_url",
            "slug", "created_at", "updated_at",
            ]
        read_only_fields = ["id", "slug", "created_at", "updated_at"]