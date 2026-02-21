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
