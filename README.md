# CIAgro Alpha

API REST para gestión agrícola. Backend construido con Django + DRF + GeoDjango sobre PostgreSQL/PostGIS.

> **Estado:** Fase 1 en progreso — Núcleo, identidad y catálogos base.

---

## Stack

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

# Instalar dependencias
pip install -r requirements.txt

# GDAL en Windows (requiere conda)
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

## Puesta en marcha

```bash
# Verificar configuración
python manage.py check

# Aplicar migraciones
python manage.py migrate

# Cargar datos iniciales de geografía
python manage.py seed_geography

# Crear superusuario
python manage.py createsuperuser

# Servidor de desarrollo
python manage.py runserver 8500
```

La API queda disponible en `http://localhost:8500/api/v1/`.

---

## Seed data

El comando `seed_geography` carga países y estados/provincias desde archivos JSON en `apps/geography/fixtures/`.

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

El comando es **idempotente**: re-ejecutarlo no crea duplicados.

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
python manage.py test apps.users
```

17 tests — modelos, autenticación, permisos, flujos de registro y perfil.

---

## Roles de acceso (RBAC)

| Nivel | Rol | Capacidades |
|-------|-----|-------------|
| 5 | SuperAdmin | Acceso completo al sistema |
| 4 | Gerente | Gestión de productores y usuarios |
| 3 | Supervisor | Lectura, actualización, validación |
| 2 | Technician | Captura de campo, carga de CSVs |
| 1 | Guest | Solo consulta de reportes |
