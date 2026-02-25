from django.urls import path
from apps.organizations.views import (
    AgroSectorListView,
    AgroSectorCreateView,
    AgroSectorDetailView,
    AgroUnitListView,
    AgroUnitCreateView,
    AgroUnitDetailView,
    AgroUnitUpdateView,
    AgroUnitDestroyView,
    ContactListView,
    ContactCreateView,
    ContactDetailView,
    ContactAssignmentCreateView
)

app_name = "organizations"

urlpatterns = [
    path("agro_sectors/", AgroSectorListView.as_view(), name="agro_sector_list"),
    path("agro_sectors/create/", AgroSectorCreateView.as_view(), name="agro_sector_create"),
    path("agro_sectors/<int:pk>/", AgroSectorDetailView.as_view(), name="agro_sector_detail"),
    path("", AgroUnitListView.as_view(), name="agro_unit_list"),
    path("create/", AgroUnitCreateView.as_view(), name="agro_unit_create"),
    path("<uuid:pk>/", AgroUnitDetailView.as_view(), name="agro_unit_detail"),
    path("<uuid:pk>/update/", AgroUnitUpdateView.as_view(), name="agro_unit_update"),
    path("<uuid:pk>/delete/", AgroUnitDestroyView.as_view(), name="agro_unit_delete"),
    path("contacts/", ContactListView.as_view(), name="contact_list"),
    path("contacts/create/", ContactCreateView.as_view(), name="contact_create"),
    path("contacts/<uuid:pk>/", ContactDetailView.as_view(), name="contact_detail"),
    path("contacts/assign/", ContactAssignmentCreateView.as_view(), name="contact_assign"),
]