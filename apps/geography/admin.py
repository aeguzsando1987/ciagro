from django.contrib import admin
from django.http import JsonResponse
from django.urls import path

from apps.geography.models import Country, State


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ["name", "iso_2", "iso_3"]
    search_fields = ["name", "iso_2", "iso_3"]
    ordering = ["name"]

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "states-for-country/",
                self.admin_site.admin_view(self.states_for_country),
                name="geography_country_states_for_country",
            ),
        ]
        return custom + urls

    def states_for_country(self, request):
        """Retorna JSON [{id, name}] de estados filtrados por ?country_id=<pk>."""
        country_id = request.GET.get("country_id")
        if not country_id:
            return JsonResponse({"states": []})
        states = (
            State.objects.filter(country_id=country_id)
            .values("id", "name")
            .order_by("name")
        )
        return JsonResponse({"states": list(states)})


@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "country"]
    list_filter = ["country"]
    search_fields = ["name", "code", "country__name"]
    ordering = ["country__name", "name"]
