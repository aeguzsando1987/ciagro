from django.urls import path

from apps.geography.views import CountryListView, StateListView

app_name = "geography"

urlpatterns = [
    path("countries/", CountryListView.as_view(), name="country-list"),
    path("states/", StateListView.as_view(), name="state-list"),
]