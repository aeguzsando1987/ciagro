from rest_framework import serializers
from apps.geography.models import Country, State

class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ["id", "name", "iso_2", "iso_3"]
        
class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = ["id", "name", "code", "country_id"]
        
class StateDetailSerializer(serializers.ModelSerializer):
    country = CountrySerializer(read_only=True)
    class Meta:
        model = State
        fields = ["id", "name", "code", "country"]

    