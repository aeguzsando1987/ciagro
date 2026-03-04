# config/settings/base.py
# Configuración común a todos los entornos (dev, prod).
# Aquí viven las apps instaladas, middleware, templates y validaciones.

from datetime import timedelta
from pathlib import Path

from decouple import config

# BASE_DIR apunta a CIAgro_alpha/ (2 niveles arriba de settings/)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# --- Seguridad ---
SECRET_KEY = config("DJANGO_SECRET_KEY", default="django-insecure-dev-key-cambiar-en-prod")

# --- Apps ---
DJANGO_APPS = [
    "jazzmin",                 # ANTES de django.contrib.admin (reemplaza templates admin)
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",  # GeoDjango: soporte PostGIS nativo
]

THIRD_PARTY_APPS = [
    "rest_framework",                              # Django REST Framework
    "rest_framework_gis",                          # Serialización GeoJSON
    "rest_framework_simplejwt.token_blacklist",    # Logout real: invalida refresh tokens
    "django_filters",                              # Filtrado en API
    "import_export",                               # Importación/exportación CSV, XLSX
    "drf_spectacular",                             # Documentación OpenAPI 3.0
]

LOCAL_APPS = [
    "apps.core",
    "apps.users",
    "apps.geography",
    "apps.organizations",
    "apps.geo_assets",
    "apps.field_ops",
    "apps.datalayers",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# --- Middleware ---
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# --- URLs y Templates ---
ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# --- Validación de passwords ---
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- Custom User Model ---
# IMPORTANTE: Definir ANTES de la primera migración.
# Se implementará en Fase 1 (apps.users.User extiende AbstractUser).
AUTH_USER_MODEL = "users.User"

# --- Internacionalización ---
LANGUAGE_CODE = "es-mx"
TIME_ZONE = "America/Mexico_City"
USE_I18N = True
USE_TZ = True

# --- Archivos estáticos ---
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# --- PK por defecto ---
# BigAutoField para tablas sin UUID explícito (tablas auxiliares/catálogos).
# Los modelos principales usarán UUIDField definido manualmente en BaseAuditModel (Fase 1).
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- DRF ---
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    # drf-spectacular genera el esquema OpenAPI 3.0 inspeccionando serializers y vistas.
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# --- drf-spectacular (OpenAPI 3.0) ---
# SPECTACULAR_SETTINGS controla los metadatos del esquema generado y
# cómo se manejan tipos especiales (GeoJSON, JWT, JSONB, paginación).
SPECTACULAR_SETTINGS = {
    # Metadatos del proyecto visibles en la cabecera de Swagger UI / ReDoc
    "TITLE": "CIAgro API",
    "DESCRIPTION": (
        "API REST del sistema de gestión agrícola CIAgro.\n\n"
        "## Autenticación\n"
        "Todos los endpoints (salvo `/auth/login/` y `/auth/register/`) requieren "
        "un **Bearer token JWT** en el header:\n"
        "```\nAuthorization: Bearer <access_token>\n```\n\n"
        "## Datos geoespaciales\n"
        "Los endpoints de `geo_assets` retornan **GeoJSON** (Feature/FeatureCollection). "
        "Los puntos en `datalayers/points/` incluyen coordenadas WGS84 (EPSG:4326) "
        "y un campo `raw_data` JSONB con los atributos medidos (pH, C, NDVI, etc.) "
        "definidos por el `definition_scheme` del `DataLayer` asociado."
    ),
    "VERSION": "1.0.0-alpha",
    "CONTACT": {"name": "CIAgro Dev Team"},
    "LICENSE": {"name": "Privado"},

    # Agrupa los endpoints por tag en la UI.
    # Los tags se asignan en cada vista con @extend_schema(tags=[...])
    "TAGS": [
        {"name": "auth",         "description": "Login, logout, tokens JWT, registro"},
        {"name": "users",        "description": "Usuarios, roles, perfiles individuales"},
        {"name": "geography",    "description": "Países y estados/provincias"},
        {"name": "organizations","description": "Unidades agrícolas, sectores, contactos"},
        {"name": "geo-assets",   "description": "Ranchos (GeoJSON), parcelas (GeoJSON), socios"},
        {"name": "field-ops",    "description": "Catálogos de cultivos/plagas, tareas de campo, reportes"},
        {"name": "datalayers",   "description": "Contratos JSONB, headers de importación, puntos georreferenciados (mapas de calor)"},
    ],

    # Seguridad: documenta que la API usa Bearer JWT
    "SECURITY": [{"BearerAuth": []}],
    "COMPONENTS": {
        "securitySchemes": {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            }
        }
    },

    # Comportamiento del generador
    "SERVE_INCLUDE_SCHEMA": False,   # Oculta el endpoint /schema/ del propio esquema
    # COMPONENT_SPLIT_REQUEST = False (no separar request/response).
    # Con True, los GeoFeatureModelSerializer fallan porque 'id' (read_only) se excluye
    # del schema de request y drf-spectacular intenta hacer pop() de un campo inexistente.
    "COMPONENT_SPLIT_REQUEST": False,
    "ENUM_GENERATE_CHOICE_DESCRIPTION": True,  # Incluye descripciones en campos choices

    # Postprocesadores: drf-spectacular incluye uno para paginación de DRF
    "POSTPROCESSING_HOOKS": [
        "drf_spectacular.hooks.postprocess_schema_enums",
    ],

    # Suprime warnings de "Could not reverse url" para modelos sin URL admin registrada.
    # Ocurre con campos FK a auth.User cuando AUTH_USER_MODEL apunta a un modelo custom.
    "DISABLE_ERRORS_AND_WARNINGS": True,

    # Configuración de Swagger UI
    "SWAGGER_UI_SETTINGS": {
        # Mantiene el token JWT entre recargas de página (localStorage del browser)
        "persistAuthorization": True,
        # Barra de búsqueda/filtro de endpoints visible por defecto
        "filter": True,
        # Muestra los schemas de request/response expandidos por defecto
        "defaultModelsExpandDepth": 2,
        "defaultModelExpandDepth": 2,
    },
}


# --- JWT ---
# ACCESS_TOKEN: vida corta (5 min) — el cliente lo usa en cada request
# REFRESH_TOKEN: vida larga (7 dias) — solo para obtener un nuevo access token
# ROTATE_REFRESH_TOKENS: cada refresh emite un nuevo refresh token (mas seguro)
# BLACKLIST_AFTER_ROTATION: el refresh token anterior queda invalidado
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=5),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# --- Celery ---
CELERY_BROKER_URL = config("REDIS_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"

# --- Jazzmin (admin branding) ---
JAZZMIN_SETTINGS = {
    "site_title": "CIAgro Admin",
    "site_header": "CIAgro",
    "site_brand": "CIAgro",
    "welcome_sign": "Bienvenido al panel de administración de CIAgro",
    "copyright": "CIAgro © 2026",
    "search_model": ["auth.User"],
    "topmenu_links": [
        {"name": "Inicio", "url": "admin:index", "permissions": ["auth.view_user"]},
        {"name": "API Docs", "url": "/api/docs/", "new_window": True},
    ],
    "show_sidebar": True,
    "navigation_expanded": True,
    "hide_apps": [],
    "order_with_respect_to": [
        "organizations", "geo_assets", "field_ops", "datalayers", "users", "geography",
    ],
    "icons": {
        "auth": "fas fa-users-cog",
        "organizations.agrounit": "fas fa-building",
        "geo_assets.ranch": "fas fa-map-marker-alt",
        "geo_assets.plot": "fas fa-draw-polygon",
        "field_ops.fieldtask": "fas fa-tasks",
        "datalayers.datalayer": "fas fa-database",
        "datalayers.datalayerheader": "fas fa-file-import",
        "datalayers.datalayerpoints": "fas fa-map-pin",
    },
    "default_icon_parents": "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",
    "related_modal_active": False,
    "custom_css": None,
    "custom_js": None,
    "use_google_fonts_cdn": True,
    "show_ui_builder": False,
    "changeform_format": "horizontal_tabs",
}
