from django.urls import path
from apps.geo_assets.views import (
    RanchListView, RanchCreateView, RanchDetailView, RanchUpdateView, RanchDestroyView,
    PlotListView, PlotCreateView, PlotDetailView, PlotUpdateView, PlotDestroyView,
    RanchPartnerListView, RanchPartnerCreateView,RanchPartnerDestroyView
)

app_name = "geo_assets"

urlpatterns = [
    # Ranch
    path("ranches/", RanchListView.as_view(), name="ranch-list"),
    path("ranches/<uuid:pk>/update/", RanchUpdateView.as_view(), name="ranch-update"),
    path("ranches/<uuid:pk>/delete/", RanchDestroyView.as_view(), name="ranch-delete"),
    path("ranches/<uuid:pk>/", RanchDetailView.as_view(), name="ranch-detail"),
    path("ranches/create/", RanchCreateView.as_view(), name="ranch-create"),
    # Plot
    path("plots/", PlotListView.as_view(), name="plot-list"),
    path("plots/create/", PlotCreateView.as_view(), name="plot-create"),
    path("plots/<uuid:pk>/", PlotDetailView.as_view(), name="plot-detail"),
    path("plots/<uuid:pk>/update/", PlotUpdateView.as_view(), name="plot-update"),
    path("plots/<uuid:pk>/delete/", PlotDestroyView.as_view(), name="plot-delete"),
    # RanchPartner
    path("ranch-partners/", RanchPartnerListView.as_view(), name="ranch-partner-list"),
    path("ranch-partners/create/", RanchPartnerCreateView.as_view(), name="ranch-partner-create"),
    path("ranch-partners/<int:pk>/delete/", RanchPartnerDestroyView.as_view(), name="ranch-partner-delete"),
]
