# CIAgro Alpha

API REST para gestión agrícola en desarrollo. Por ahora solo se esta constryendo el backend utilizando  Django + DRF + GeoDjango sobre PostgreSQL/PostGIS, dado que muhcos datos son georeferenciados.

> **Estado actual:** Fase 2 completada — Organizaciones y activos geográficos. Próximo: Fase 3 (operación en campo y motor de datos).

---

## Stack actual

| Componente | Tecnología |
|---|---|
| Lenguaje | Python 3.12 |
| Framework | Django 5.1 + Django REST Framework |
| Autenticación | djangorestframework-simplejwt (JWT) |
| Base de datos | PostgreSQL + PostGIS |
| Geodatos | GeoDjango + GDAL + GEOS + PROJ |
| Tareas async | Celery + Redis (configurado) |
| Contenerización | Docker (configurado, no activo en dev) |

---

## Requisitos previos

- Python 3.12
- PostgreSQL con extensión PostGIS
- Conda (solo en Windows, para GDAL)

***Nota:** GDAL permite leer/escritura de formatos geoespaciales (Shapefile, GeoJSON, etc.)

---

## Instalación

```bash
# Clonar y entrar al proyecto
git clone <repo>
cd CIAgro_alpha

# Crear y activar entorno virtual
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/macOS

# Instalar las dependencias
pip install -r requirements.txt

# instalar GDAL en Windows (requiere conda)
conda install -c conda-forge gdal
```

---

## Configuración

### Variables de entorno

Crear archivo `.env` en la raíz del proyecto:

```env
POSTGRES_DB=ciagro_db_alpha_v1
POSTGRES_USER=ciagro_user
POSTGRES_PASSWORD=ciagro_pass
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

DJANGO_SECRET_KEY=cambia-esto-por-un-valor-secreto
DJANGO_DEBUG=True
DJANGO_SETTINGS_MODULE=config.settings.dev
```

### Base de datos

```sql
-- En psql como superusuario:
CREATE DATABASE ciagro_db_alpha_v1;
CREATE USER ciagro_user WITH PASSWORD 'ciagro_pass';
GRANT ALL PRIVILEGES ON DATABASE ciagro_db_alpha_v1 TO ciagro_user;
ALTER USER ciagro_user SUPERUSER;  -- requerido para PostGIS en tests
```

---

## Para desarrollo y pruebas

```bash
# Verificar configuración
python manage.py check

# Aplicar migraciones
python manage.py migrate

# Cargar datos iniciales de geografía
python manage.py seed_geography

# Crear superusuario
python manage.py createsuperuser

# Servidor de desarrollo local con puerto por defecto de django
python manage.py runserver 8500
```

La API queda disponible en `http://localhost:8500/api/v1/`.

---

## Seed data

Con el comando `seed_geography` se pueden cargar países y estados/provincias desde archivos JSON en `apps/geography/fixtures/`. El contenido del archivo `countries.json` es el mismo que el de [ISO 3166-2](https://en.wikipedia.org/wiki/ISO_3166-2:MX). El archivo `states.json` esta basado en [ISO 3166-2](https://en.wikipedia.org/wiki/ISO_3166-2:MX). La carga de estados/provincias esta limitada a a Mexico, Estados Unidos, España, Colombia, Argentina, Chile, Canadá y Uruguay. Edite el archivo para agregar estados correspondientes a su pais.
```bash
# Carga completa (países + estados)
python manage.py seed_geography

# Solo países
python manage.py seed_geography --only-countries

# Solo estados (requiere países en BD)
python manage.py seed_geography --only-states

# Archivos personalizados
python manage.py seed_geography \
  --countries-file /ruta/paises.json \
  --states-file /ruta/estados.json

# Limpiar y recargar desde cero
python manage.py seed_geography --reset
```

**Datos incluidos:**

| Fixture | Contenido |
|---------|-----------|
| `countries.json` | 193 países — nombres en español, iso_2, iso_3 |
| `states.json` | 223 entidades — estados/provincias de MX, US, ES, CO, AR, CL, CA, UY |

El comando es **idempotente**: re-ejecutarlo va a crear datos duplicados en la base de datos.

---

## API Endpoints

### Autenticación

| Método | URL | Descripción | Permiso |
|--------|-----|-------------|---------|
| POST | `/api/v1/auth/login/` | Obtener access + refresh token | Público |
| POST | `/api/v1/auth/refresh/` | Renovar access token | Público |
| POST | `/api/v1/auth/logout/` | Invalidar refresh token | Autenticado |
| POST | `/api/v1/auth/change-password/` | Cambiar contraseña | Autenticado |
| POST | `/api/v1/auth/register/` | Crear usuario (admin) | SuperAdmin |
| POST | `/api/v1/auth/signup/` | Registro público | Público |

### Usuarios

| Método | URL | Descripción | Permiso |
|--------|-----|-------------|---------|
| GET | `/api/v1/users/` | Listar usuarios | SuperAdmin |
| GET | `/api/v1/users/me/` | Perfil propio | Autenticado |
| PATCH | `/api/v1/users/me/` | Editar perfil | Autenticado |
| GET | `/api/v1/users/roles/` | Listar roles de acceso | Autenticado |
| GET | `/api/v1/users/work-roles/` | Listar roles laborales | Autenticado |

### Geografía

| Método | URL | Descripción | Permiso |
|--------|-----|-------------|---------|
| GET | `/api/v1/geography/countries/` | Listar países | Autenticado |
| GET | `/api/v1/geography/states/` | Listar estados | Autenticado |
| GET | `/api/v1/geography/states/?country=MX` | Filtrar estados por país (iso_2) | Autenticado |

### Organizaciones

| Método | URL | Descripción | Permiso |
|--------|-----|-------------|---------|
| GET | `/api/v1/organizations/` | Listar AgroUnits (scope filter) | Autenticado |
| POST | `/api/v1/organizations/create/` | Crear AgroUnit | SuperAdmin |
| GET | `/api/v1/organizations/<uuid>/` | Detalle AgroUnit | Autenticado |
| PATCH | `/api/v1/organizations/<uuid>/update/` | Actualizar AgroUnit | SuperAdmin |
| DELETE | `/api/v1/organizations/<uuid>/delete/` | Soft delete AgroUnit | SuperAdmin |
| GET | `/api/v1/organizations/agro_sectors/` | Listar sectores agrícolas | Autenticado |
| POST | `/api/v1/organizations/agro_sectors/create/` | Crear sector | SuperAdmin |
| GET | `/api/v1/organizations/agro_sectors/<id>/` | Detalle sector | Autenticado |
| GET | `/api/v1/organizations/contacts/` | Listar contactos | Autenticado |
| POST | `/api/v1/organizations/contacts/create/` | Crear contacto | Autenticado |
| GET | `/api/v1/organizations/contacts/<uuid>/` | Detalle contacto | Autenticado |
| POST | `/api/v1/organizations/contacts/assign/` | Asignar contacto a AgroUnit | Autenticado |

> **Multi-tenancy:** usuarios sin rol SuperAdmin solo ven las AgroUnits que tienen asignadas vía `UserAssignment`.

### Activos geográficos

> **Formato GeoJSON:** los endpoints de Ranch y Plot producen y consumen GeoJSON Feature.
> POST requiere: `{"type": "Feature", "geometry": null, "properties": {...}}`
> Las respuestas de lista son FeatureCollection paginado: `{"results": {"type": "FeatureCollection", "features": [...]}, "count": N, ...}`

| Método | URL | Descripción | Permiso |
|--------|-----|-------------|---------|
| GET | `/api/v1/geo_assets/ranches/` | Listar ranchos (scope filter, GeoJSON) | Autenticado |
| POST | `/api/v1/geo_assets/ranches/create/` | Crear rancho | SuperAdmin |
| GET | `/api/v1/geo_assets/ranches/<uuid>/` | Detalle rancho (GeoJSON) | Autenticado |
| PATCH | `/api/v1/geo_assets/ranches/<uuid>/update/` | Actualizar rancho | SuperAdmin |
| DELETE | `/api/v1/geo_assets/ranches/<uuid>/delete/` | Soft delete rancho | SuperAdmin |
| GET | `/api/v1/geo_assets/plots/` | Listar parcelas (scope filter, GeoJSON) | Autenticado |
| POST | `/api/v1/geo_assets/plots/create/` | Crear parcela | SuperAdmin |
| GET | `/api/v1/geo_assets/plots/<uuid>/` | Detalle parcela (GeoJSON) | Autenticado |
| PATCH | `/api/v1/geo_assets/plots/<uuid>/update/` | Actualizar parcela | SuperAdmin |
| DELETE | `/api/v1/geo_assets/plots/<uuid>/delete/` | Soft delete parcela | SuperAdmin |
| GET | `/api/v1/geo_assets/ranch-partners/` | Listar relaciones rancho-socio | Autenticado |
| GET | `/api/v1/geo_assets/ranch-partners/?ranch=<uuid>` | Filtrar por rancho | Autenticado |
| POST | `/api/v1/geo_assets/ranch-partners/create/` | Crear relación (valida tipo) | SuperAdmin |
| DELETE | `/api/v1/geo_assets/ranch-partners/<id>/delete/` | Eliminar relación (hard delete) | SuperAdmin |

> **Scope filter geo_assets:** Ranch filtra por `producer_id__in`; Plot filtra por `ranch__producer_id__in`.
> **RanchPartner:** pivote puro sin soft delete. Valida coherencia entre `relation_type` y `partner.unit_type`.

### Autenticación por token

```http
Authorization: Bearer <access_token>
```

---

## Estructura del proyecto

```
CIAgro_alpha/
├── config/
│   ├── settings/
│   │   ├── base.py       # Configuración común
│   │   ├── dev.py        # Entorno local (DEBUG, GDAL paths)
│   │   └── prod.py       # Producción (pendiente)
│   └── urls.py
├── apps/
│   ├── core/             # BaseAuditModel (abstracto)
│   ├── users/            # Auth, roles, perfiles
│   ├── geography/        # Países, estados, seed data
│   ├── organizations/    # AgroUnits (Fase 2)
│   ├── geo_assets/       # Ranchos, parcelas (Fase 2)
│   ├── field_ops/        # Tareas de campo (Fase 3)
│   └── datalayers/       # Motor JSONB (Fase 3)
├── manage.py
├── requirements.txt
└── docker-compose.yml
```

---

## Tests

```bash
# Ejecutar todos los tests
python manage.py test apps.users apps.geography apps.organizations apps.geo_assets

# Por app
python manage.py test apps.users          # 25 tests — auth, roles, perfiles, soft delete
python manage.py test apps.geography      # 32 tests — países, estados, seed data
python manage.py test apps.organizations  # 15 tests — AgroSector, AgroUnit, scope filter
python manage.py test apps.geo_assets     # 23 tests — Ranch, RanchScope, Plot, RanchPartner
```

**Total: ~95 tests** cubriendo modelos, permisos, multi-tenancy, scope filter y GeoJSON.

---

## Roles de acceso (RBAC)

| Nivel | Rol | Capacidades |
|-------|-----|-------------|
| 5 | SuperAdmin | Acceso completo al sistema |
| 4 | Gerente | Gestión de productores y usuarios |
| 3 | Supervisor | Lectura, actualización, validación |
| 2 | Technician | Captura de campo, carga de CSVs |
| 1 | Guest | Solo consulta de reportes |
