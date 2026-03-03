from django.urls import path
from apps.datalayers.views import (
    DataLayerListView,
    DataLayerCreateView,
    DataLayerDetailView,
    DataLayerUpdateView,
    DataLayerHeaderListView,
    DataLayerHeaderCreateView,
    DataLayerHeaderDetailView,
    DataLayerHeaderUpdateView,
    DataLayerHeaderImportView,
    DataLayerPointsListView,
    DataLayerPointsCreateView,
    DataLayerPointsDetailView,
)

app_name = "datalayers"

urlpatterns = [
    path("", DataLayerListView.as_view(), name="datalayer-list"),
    path("create/", DataLayerCreateView.as_view(), name="datalayer-create"),
    path("<int:pk>/", DataLayerDetailView.as_view(), name="datalayer-detail"),
    path("<int:pk>/update/", DataLayerUpdateView.as_view(), name="datalayer-update"),

    path("headers/", DataLayerHeaderListView.as_view(), name="datalayerheader-list"),
    path("headers/create/", DataLayerHeaderCreateView.as_view(), name="datalayerheader-create"),
    # IMPORTANTE: import/ debe ir ANTES de <uuid:pk>/ para que Django no intente
    # interpretar la palabra "import" como un UUID (fallaría silenciosamente).
    path("headers/import/", DataLayerHeaderImportView.as_view(), name="datalayerheader-import"),
    path("headers/<uuid:pk>/", DataLayerHeaderDetailView.as_view(), name="datalayerheader-detail"),
    path("headers/<uuid:pk>/update/", DataLayerHeaderUpdateView.as_view(), name="datalayerheader-update"),

    path("points/", DataLayerPointsListView.as_view(), name="datalayerpoints-list"),
    path("points/create/", DataLayerPointsCreateView.as_view(), name="datalayerpoints-create"),
    path("points/<uuid:pk>/", DataLayerPointsDetailView.as_view(), name="datalayerpoints-detail"),
    # Sin ruta update: los puntos cargados son inmutables una vez creados.
]