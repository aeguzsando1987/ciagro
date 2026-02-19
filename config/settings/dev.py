# config/settings/dev.py
# Configuración de DESARROLLO. Extiende base.py.
# Uso: DJANGO_SETTINGS_MODULE=config.settings.dev

from .base import *  # noqa: F401,F403

DEBUG = True

# --- GeoDjango: rutas a librerías GDAL/GEOS en Windows (vía Anaconda) ---
# En Linux/Docker estas rutas no son necesarias (se detectan automáticamente).
# En Windows, Django necesita saber dónde están las DLLs de GDAL y GEOS.
GDAL_LIBRARY_PATH = r"C:\Users\E-IPC-L_36\anaconda3\Library\bin\gdal.dll"
GEOS_LIBRARY_PATH = r"C:\Users\E-IPC-L_36\anaconda3\Library\bin\geos_c.dll"
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

# --- BD: PostGIS ---
# Para Docker: HOST default = "db" (nombre del servicio en docker-compose)
# Para local:  HOST default = "localhost"
DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",  # Motor GeoDjango (no el genérico)
        "NAME": config("POSTGRES_DB", default="ciagro_db"),
        "USER": config("POSTGRES_USER", default="ciagro_user"),
        "PASSWORD": config("POSTGRES_PASSWORD", default="ciagro_pass"),
        # "HOST": config("POSTGRES_HOST", default="db"),  # Docker
        "HOST": config("POSTGRES_HOST", default="localhost"),  # Local
        "PORT": config("POSTGRES_PORT", default="5432"),
    }
}
