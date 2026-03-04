"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),

    # --- Documentación OpenAPI 3.0 (Fase C) ---
    # C2: Esquema bruto descargable (JSON o YAML según ?format=)
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    # C3: Swagger UI — exploración interactiva de la API
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    # C4: ReDoc — documentación legible para terceros
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("api/v1/", include("apps.users.urls")),
    path("api/v1/geography/", include("apps.geography.urls")),
    path("api/v1/organizations/", include("apps.organizations.urls")),
    path("api/v1/geo_assets/", include("apps.geo_assets.urls")),
    path("api/v1/field_ops/", include("apps.field_ops.urls")),
    path("api/v1/datalayers/", include("apps.datalayers.urls")),
]
