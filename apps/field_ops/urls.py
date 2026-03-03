from django.urls import path
from apps.field_ops.views import (
    CropCatalogListView, CropCatalogCreateView,
    CropCatalogDetailView, CropCatalogUpdateView,
    PestCatalogListView, PestCatalogCreateView,
    PestCatalogDetailView, PestCatalogUpdateView,
    FieldTaskListView, FieldTaskCreateView,
    FieldTaskDetailView, FieldTaskUpdateView,
    GenerateReportView,
)

app_name = "field_ops"

urlpatterns = [
    path("crops/", CropCatalogListView.as_view(), name="crop-list"),
    path("crops/create/", CropCatalogCreateView.as_view(), name="crop-create"),
    path("crops/<int:pk>/", CropCatalogDetailView.as_view(), name="crop-detail"),
    path("crops/<int:pk>/update/", CropCatalogUpdateView.as_view(), name="crop-update"),
    path("pests/", PestCatalogListView.as_view(), name="pest-list"),
    path("pests/create/", PestCatalogCreateView.as_view(), name="pest-create"),
    path("pests/<int:pk>/", PestCatalogDetailView.as_view(), name="pest-detail"),
    path("pests/<int:pk>/update/", PestCatalogUpdateView.as_view(), name="pest-update"),
    path("tasks/", FieldTaskListView.as_view(),   name="task-list"),
    path("tasks/create/", FieldTaskCreateView.as_view(), name="task-create"),
    path("tasks/<uuid:pk>/", FieldTaskDetailView.as_view(), name="task-detail"),
    path("tasks/<uuid:pk>/update/", FieldTaskUpdateView.as_view(), name="task-update"),
    path("tasks/<uuid:pk>/generate-report/", GenerateReportView.as_view(), name="task-generate-report"),
]
