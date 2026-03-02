from rest_framework import serializers
from apps.datalayers.models import DataLayer

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