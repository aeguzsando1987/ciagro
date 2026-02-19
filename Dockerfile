# Dockerfile — CIAgro Alpha
# Imagen base con Python 3.12 sobre Debian (necesario para librerías geoespaciales C)
FROM python:3.12-slim-bookworm

# Variables de entorno para Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instalacion de dependencias del sistema para GeoDjango
# - gdal-bin, libgdal-dev: lectura/escritura de formatos geoespaciales (Shapefile, GeoJSON, etc.)
# - libgeos-dev: operaciones geométricas (intersección, buffer, distancia)
# - libproj-dev: transformación de coordenadas entre sistemas de referencia (SRID)
# - postgresql-client: para manage.py dbshell y pg_isready
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia e instalacion de dependencias Python (cache de Docker layers)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia del resto del código
COPY . .

# Puerto de Django
EXPOSE 8500

# Comando por defecto: servidor de desarrollo / cambiar cuando se use en produccion
CMD ["python", "manage.py", "runserver", "0.0.0.0:8500"]
