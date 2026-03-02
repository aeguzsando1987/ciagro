from django.urls import path
from apps.datalayers.views import (
    DataLayerListView,
    DataLayerCreateView,
    DataLayerDetailView,
    DataLayerUpdateView
)

app_name = "datalayers"

urlpatterns = [
    path("", DataLayerListView.as_view(), name="datalayer-list"),
    path("create/", DataLayerCreateView.as_view(), name="datalayer-create"),
    path("<int:pk>/", DataLayerDetailView.as_view(), name="datalayer-detail"),
    path("<int:pk>/update/", DataLayerUpdateView.as_view(), name="datalayer-update"),
]