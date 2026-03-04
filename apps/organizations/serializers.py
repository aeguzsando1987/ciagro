from rest_framework import serializers
from apps.organizations.models import AgroSector, AgroUnit, Contact, ContactAssignment

class AgroSectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgroSector
        fields = ["id", "sector_name", "scian_code", "activity_name", "description"]


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ["id", "name", "address_line_1", "address_line_2",
                "phone", "email", "slug", "created_at", "updated_at"]
        read_only_fields = ["id", "slug", "created_at", "updated_at"]


class AgroUnitSerializer(serializers.ModelSerializer):
    agro_sector = AgroSectorSerializer(read_only=True)
    agro_sector_id = serializers.PrimaryKeyRelatedField(
        queryset=AgroSector.objects.all(),
        source="agro_sector",
        write_only=True,
        required=False,
        allow_null=True
    )
    default_contact = ContactSerializer(read_only=True)
    default_contact_id = serializers.PrimaryKeyRelatedField(
        queryset=Contact.objects.filter(is_deleted=False),
        source="default_contact",
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
            "default_contact", "default_contact_id",
            "status", "additional_params", "attachments_url",
            "slug", "created_at", "updated_at",
            ]
        read_only_fields = ["id", "slug", "created_at", "updated_at"]

    def validate(self, data):
        country = data.get("country") or (self.instance.country if self.instance else None)
        state = data.get("state")
        if state and country and state.country_id != country.id:
            raise serializers.ValidationError(
                {"state": "El estado no pertenece al país seleccionado."}
            )
        return data


class ContactAssignmentSerializer(serializers.ModelSerializer):
    contact = ContactSerializer(read_only=True)
    contact_id = serializers.PrimaryKeyRelatedField(
        queryset=Contact.objects.all(),
        source="contact",
        write_only=True
    )
    agro_unit = AgroUnitSerializer(read_only=True)
    agro_unit_id = serializers.PrimaryKeyRelatedField(
        queryset=AgroUnit.objects.filter(is_deleted=False),
        source="agro_unit",
        write_only=True
    )
    class Meta:
        model = ContactAssignment
        fields = ["id", "contact", "contact_id", "agro_unit", "agro_unit_id", "created_at"]
        read_only_fields = ["id", "created_at"]
