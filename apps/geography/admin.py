from django.contrib import admin

from apps.geography.models import Country, State


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ["name", "iso_2", "iso_3"]
    search_fields = ["name", "iso_2", "iso_3"]
    ordering = ["name"]


@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "country"]
    list_filter = ["country"]
    search_fields = ["name", "code", "country__name"]
    ordering = ["country__name", "name"]
