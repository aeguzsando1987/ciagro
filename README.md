# CIAgro Alpha

Backend de gestión agrícola construido con Django + DRF + GeoDjango sobre PostgreSQL/PostGIS.
Expone una API REST para la gestión de organizaciones, activos geográficos, operaciones de campo y captura masiva de datos georreferenciados (DataLayers).

> **Estado actual:** Fase E en progreso — 86% completado (72/84 pasos).
> Fases 0–D completadas. Pendiente: E2–E3 (features complejos) y Fase F (dockerización).

---

## Stack

| Componente | Tecnología |
|---|---|
| Lenguaje | Python 3.12 |
| Framework | Django 5.1 + Django REST Framework 3.15 |
| Autenticación | djangorestframework-simplejwt (JWT) |
| Base de datos | PostgreSQL + PostGIS |
| Geodatos | GeoDjango + GDAL + GEOS + PROJ |
| Tareas async | Celery 5.4 + Redis 7 |
| Admin UI | django-jazzmin 3.0 |
| Documentación API | drf-spectacular (OpenAPI 3.0 / Swagger UI) |
| Contenerización | Docker (Redis en dev, full stack en Fase F) |

---

## Setup completo — primera vez (checklist secuencial)

Sigue estos pasos **en orden**. Las secciones siguientes explican cada uno en detalle.

```
[ ] 1. Instalar requisitos del sistema (Python 3.12, PostgreSQL, Docker Desktop, Conda)
[ ] 2. Clonar el repositorio e instalar dependencias Python
[ ] 3. Instalar GDAL via Conda (solo Windows)
[ ] 4. Crear el archivo .env con las variables de entorno
[ ] 5. Crear la base de datos en PostgreSQL y activar PostGIS
[ ] 6. Levantar Redis:    docker-compose up -d redis
[ ] 7. Aplicar migraciones:   python manage.py migrate
[ ] 8. Cargar países y estados:  python manage.py seed_geography
[ ] 9. Crear usuario admin:   python manage.py createsuperuser
[ ] 10. Levantar Celery (terminal separada):
        celery -A config worker -l info --pool=solo
[ ] 11. Levantar Django (terminal separada):
        python manage.py runserver 0.0.0.0:8500
[ ] 12. Verificar acceso al admin:  http://localhost:8500/admin/
[ ] 13. Verificar API con login:    POST http://localhost:8500/api/v1/auth/login/
```

> **Nota:** no existe archivo `.env.example`. Crea el `.env` desde cero usando
> la plantilla de la sección **Configuración** más abajo.

A partir del segundo arranque solo necesitas los pasos 6, 10 y 11 (Redis + Celery + Django).

---

## Requisitos previos

- Python 3.12
- PostgreSQL 14+ con extensión PostGIS
- Docker Desktop (para Redis en desarrollo)
- Conda (solo en Windows, para instalar GDAL)

> **¿Por qué Conda para GDAL en Windows?**
> Los binarios de GDAL para Windows no están disponibles en PyPI. Conda los provee
> precompilados con todas las dependencias geoespaciales (GEOS, PROJ, GDAL).

---

## Instalación

```bash
# 1. Clonar el repositorio
git clone <repo>
cd CIAgro_alpha

# 2. Crear y activar entorno virtual
python -m venv venv
venv\Scripts\activate        # Windows (cmd/PowerShell)
source venv/Scripts/activate # Windows (Git Bash) ← recomendado
# source venv/bin/activate   # Linux/macOS

# 3. Instalar dependencias Python
pip install -r requirements.txt

# 4. Instalar GDAL (solo Windows, requiere conda en PATH)
conda install -c conda-forge gdal
```

---

## Configuración

### Variables de entorno

Crear archivo `.env` en la raíz del proyecto (mismo nivel que `manage.py`):

```env
# Base de datos
POSTGRES_DB=ciagro_db_alpha_v1
POSTGRES_USER=ciagro_user
POSTGRES_PASSWORD=ciagro_pass
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Django
DJANGO_SECRET_KEY=cambia-esto-por-un-valor-secreto-largo
DJANGO_DEBUG=True
DJANGO_SETTINGS_MODULE=config.settings.dev

# Redis / Celery
REDIS_URL=redis://localhost:6380/0

# Superusuario inicial (usado por createsuperuser --noinput)
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@ciagro.mx
DJANGO_SUPERUSER_PASSWORD=cambiar_en_produccion
```

### Base de datos PostgreSQL

Ejecutar como superusuario de PostgreSQL:

```sql
CREATE DATABASE ciagro_db_alpha_v1;
CREATE USER ciagro_user WITH PASSWORD 'ciagro_pass';
GRANT ALL PRIVILEGES ON DATABASE ciagro_db_alpha_v1 TO ciagro_user;
ALTER USER ciagro_user SUPERUSER;  -- requerido para crear la BD de tests con PostGIS

-- Conectar a la base de datos y activar PostGIS
\c ciagro_db_alpha_v1
CREATE EXTENSION IF NOT EXISTS postgis;
```

> **Nota:** Django no crea la base de datos automáticamente. Solo crea las tablas
> dentro de una BD que ya existe. El paso anterior es obligatorio antes de `migrate`.

---

## Arranque del sistema

El sistema necesita **tres procesos corriendo simultáneamente** para funcionar completo.
Usar tres terminales separadas.

### Terminal 1 — Redis (broker de Celery)

```bash
# Levanta Redis en Docker en puerto 6380
docker-compose up -d redis
```

### Terminal 2 — Celery worker (tareas asíncronas)

```bash
cd CIAgro_alpha
source venv/Scripts/activate
celery -A config worker -l info --pool=solo
```

> `--pool=solo` es obligatorio en Windows. En Linux/macOS se puede omitir.
> Celery procesa la importación masiva de CSVs (DataLayerPoints).

### Terminal 3 — Django (servidor de desarrollo)

```bash
cd CIAgro_alpha
source venv/Scripts/activate
python manage.py runserver 0.0.0.0:8500
```

La API queda disponible en `http://localhost:8500/api/v1/`.
El admin queda disponible en `http://localhost:8500/admin/`.

---

## Primer arranque (base de datos vacía)

```bash
# 1. Crear tablas (aplica todas las migraciones en orden)
python manage.py migrate

# 2. Cargar datos iniciales de geografía (países y estados)
python manage.py seed_geography

# 3. Crear el primer usuario administrador (ver detalle abajo)
python manage.py createsuperuser
```

### Crear el primer usuario administrador

> **Para pruebas locales:** con solo crear este usuario ya puedes entrar al admin
> y consumir todos los endpoints de la API con curl. No necesitas crear usuarios
> adicionales ni configurar nada más para explorar el sistema.

Este paso es obligatorio para poder acceder al admin y consumir la API.
`createsuperuser` crea un usuario con `is_superuser=True` e `is_staff=True` en Django,
que se traduce a `user_role=5` (SuperAdmin) en el sistema CIAgro.

**Opción A — Interactivo (recomendado para desarrollo):**

```bash
python manage.py createsuperuser
```

Django te pedirá los datos uno a uno:

```
Username: admin
Email address: admin@ciagro.mx
Password: ************
Password (again): ************
Superuser created successfully.
```

**Opción B — Sin interacción (usando variables del `.env`):**

Asegúrate de tener estas tres variables en tu `.env`:

```env
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@ciagro.mx
DJANGO_SUPERUSER_PASSWORD=cambiar_en_produccion
```

Luego ejecuta:

```bash
python manage.py createsuperuser --noinput
```

**Verificar que el usuario fue creado** — ingresa al admin:

```
http://localhost:8500/admin/
Usuario:    admin
Contraseña: la que configuraste
```

Si entras al panel correctamente, el usuario existe y tienes acceso completo al sistema.

**Este mismo usuario sirve para consumir la API** — usa sus credenciales en el login:

```bash
curl -X POST http://localhost:8500/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "tu_password"}'
```

---

## Seed data de geografía

El comando `seed_geography` carga países y estados desde archivos JSON en `apps/geography/fixtures/`.
Es **idempotente**: re-ejecutarlo no genera duplicados (usa `get_or_create`).

```bash
# Carga completa (países + estados)
python manage.py seed_geography

# Solo países
python manage.py seed_geography --only-countries

# Solo estados (requiere que los países ya existan)
python manage.py seed_geography --only-states

# Limpiar y recargar desde cero
python manage.py seed_geography --reset
```

| Fixture | Contenido |
|---|---|
| `countries.json` | 193 países — nombres en español, iso_2, iso_3 |
| `states.json` | 223 entidades — estados/provincias de MX, US, ES, CO, AR, CL, CA, UY |

---

## Tests

```bash
# Todos los tests
python manage.py test apps -v 2

# Por app
python manage.py test apps.users           # ~25 tests — auth, roles, perfiles, soft delete
python manage.py test apps.geography       # ~32 tests — países, estados, seed data
python manage.py test apps.organizations   # ~15 tests — AgroSector, AgroUnit, scope filter
python manage.py test apps.geo_assets      # ~23 tests — Ranch, Plot, RanchPartner, geom auto-calc
python manage.py test apps.field_ops       # ~28 tests — CropCatalog, PestCatalog, FieldTask, Report
python manage.py test apps.datalayers      # ~43 tests — DataLayer, Header, Points, CSV import, bulk
python manage.py test apps.core            # ~8 tests  — Attachment API
```

**Total: ~174 tests** cubriendo modelos, permisos, multi-tenancy, scope filter, GeoJSON,
validación JSONB, importación masiva (bulk 60k+) y archivos adjuntos.

> Los tests requieren que `ciagro_user` tenga rol `SUPERUSER` en PostgreSQL
> para poder crear y destruir la base de datos de prueba con la extensión PostGIS.

---

## Acceso al Admin

El admin de Django es la interfaz web principal para gestionar datos del sistema.

**URL:** `http://localhost:8500/admin/`

**Credenciales:** las que configuraste en el paso `createsuperuser`
(o las variables `DJANGO_SUPERUSER_USERNAME` / `DJANGO_SUPERUSER_PASSWORD` del `.env`).

Una vez dentro verás el panel lateral izquierdo con todas las apps registradas:
`CORE`, `DATALAYERS`, `FIELD_OPS`, `GEO_ASSETS`, `GEOGRAPHY`, `ORGANIZATIONS`, `USERS`.
Cada sección lista sus modelos — haz clic en cualquiera para ver, crear o editar registros.

---

## Documentación API

Con el servidor corriendo:

| URL | Descripción |
|---|---|
| `http://localhost:8500/api/docs/` | Swagger UI interactivo |
| `http://localhost:8500/api/redoc/` | ReDoc (para terceros) |
| `http://localhost:8500/api/schema/` | OpenAPI 3.0 JSON/YAML |

La documentación incluye todos los endpoints con ejemplos de request/response,
parámetros de filtro y autenticación JWT integrada.

### Cómo acceder desde el admin

No hay un link directo en el panel lateral. Accede por URL directa mientras el servidor corre:

- Swagger UI → `http://localhost:8500/api/docs/`
- ReDoc      → `http://localhost:8500/api/redoc/`
- JSON crudo → `http://localhost:8500/api/schema/`

### Cómo leer ReDoc

ReDoc organiza la documentación en tres zonas:

```
[ Panel izquierdo ]     [ Panel central ]          [ Panel derecho ]
  Indice de             Descripcion del            Ejemplos de
  endpoints             endpoint:                  request/response
  agrupados             - Metodo y URL             en JSON
  por tag               - Descripcion
  (auth, users,         - Parametros
  geo_assets...)        - Request body
                        - Respuestas posibles
```

**Como navegar:**
1. Panel izquierdo → busca el tag del area que te interesa (ej: `datalayers`)
2. Expande el tag → aparecen todos sus endpoints
3. Clic en un endpoint → el panel central muestra su descripcion completa
4. Panel derecho → schema del body esperado y schema de la respuesta

**Que significa cada seccion del panel central:**

| Seccion | Que contiene |
|---|---|
| **Parameters** | Parametros en la URL (`path`) o query string (`?key=value`) |
| **Request Body** | El JSON que debes enviar en el body del POST/PATCH |
| **Responses** | Codigos HTTP posibles y el schema del JSON devuelto |
| **required** | Campo obligatorio — si falta, la API devuelve 400 |

### Como usar Swagger UI para probar endpoints

Swagger UI permite ejecutar requests directamente desde el browser.

1. Abre `http://localhost:8500/api/docs/`
2. Clic en **Authorize** (boton candado, arriba a la derecha)
3. En el campo `bearerAuth` pega solo el token (sin la palabra `Bearer`)
4. Clic en **Authorize** → **Close**
5. Busca el endpoint → **Try it out** → completa los campos → **Execute**
6. Veras el curl equivalente, el request enviado y la respuesta real del servidor

---

## curl en Windows

Los ejemplos de esta guía usan sintaxis Unix. El comportamiento de curl varía según la terminal
que uses en Windows:

---

### Opción A — Git Bash (recomendado)

Git Bash interpreta la sintaxis Unix directamente. **Todos los ejemplos de esta guía
funcionan sin modificación** en Git Bash.

```bash
# Funciona igual que en Linux/macOS
curl -X POST http://localhost:8500/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "tu_password"}'
```

---

### Opción B — Command Prompt (cmd.exe)

cmd.exe **no soporta comillas simples** en el body JSON. Debes:
1. Reemplazar comillas simples `'` por comillas dobles `"`
2. Escapar las comillas internas del JSON con `\"`
3. No usar `$()` — copiar y pegar el token manualmente

```cmd
:: Login
curl -X POST http://localhost:8500/api/v1/auth/login/ ^
  -H "Content-Type: application/json" ^
  -d "{\"username\": \"admin\", \"password\": \"tu_password\"}"

:: Usar token (pegar el valor de "access" directamente)
curl http://localhost:8500/api/v1/users/me/ ^
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

> `^` es el carácter de continuación de línea en cmd.exe (equivale a `\` en bash).

---

### Opción C — PowerShell

PowerShell tiene su propio comando nativo `Invoke-RestMethod` (alias: `irm`) que maneja
JSON de forma más limpia que curl. También puedes usar `curl.exe` (con la extensión `.exe`
para evitar conflicto con el alias de PowerShell).

**Con `Invoke-RestMethod`:**
```powershell
# Login y capturar token en variable
$resp = Invoke-RestMethod -Method Post `
  -Uri "http://localhost:8500/api/v1/auth/login/" `
  -ContentType "application/json" `
  -Body '{"username": "admin", "password": "tu_password"}'

$TOKEN = $resp.access

# Usar el token
Invoke-RestMethod -Uri "http://localhost:8500/api/v1/users/me/" `
  -Headers @{ Authorization = "Bearer $TOKEN" }
```

**Con `curl.exe` (si prefieres curl):**
```powershell
# En PowerShell, "curl" es un alias de Invoke-WebRequest.
# Usa "curl.exe" para invocar el curl real de Windows.
curl.exe -X POST http://localhost:8500/api/v1/auth/login/ `
  -H "Content-Type: application/json" `
  -d '{\"username\": \"admin\", \"password\": \"tu_password\"}'
```

> `` ` `` es el carácter de continuación de línea en PowerShell (equivale a `\` en bash).

---

### Tabla resumen

| Terminal | Comillas en JSON | Continuación de línea | Capturar token |
|---|---|---|---|
| **Git Bash** | `'{"key": "val"}'` | `\` | `TOKEN=$(...)` |
| **cmd.exe** | `"{\"key\": \"val\"}"` | `^` | Copiar manualmente |
| **PowerShell** | `'{"key": "val"}'` | `` ` `` | `$TOKEN = (irm ...).access` |

**Recomendación:** usa Git Bash para seguir los ejemplos de esta guía sin adaptaciones.

---

## Guia rapida: consumir la API

### Paso 1 — Login: obtener el token

El primer paso siempre es autenticarse. La API devuelve dos tokens: `access` (corta duracion,
~60 min, se usa en cada request) y `refresh` (larga duracion, solo para renovar el `access`).

> **Importante:** el login requiere `username` + `password`.
> El email existe en el modelo pero **no se usa para autenticarse** — no lo envíes aquí.

**Request:**
```bash
curl -X POST http://localhost:8500/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "tu_password"}'
```

**Response exitosa (200):**
```json
{
  "access":  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiMTIzIn0...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiMTIzIn0..."
}
```

Guarda el valor de `access`. Lo necesitas en todos los requests siguientes.

---

### Paso 2 — Usar el token en cada request

Incluye el token en el header `Authorization` con el prefijo `Bearer`:

```bash
curl http://localhost:8500/api/v1/users/me/ \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response (200):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "admin",
  "email": "admin@ciagro.mx",
  "user_role": 5,
  "is_active": true
}
```

---

### Paso 3 — Renovar el token cuando expira

Cuando el `access` expira la API responde `401`. Usa el `refresh` para obtener uno nuevo
sin volver a hacer login:

```bash
curl -X POST http://localhost:8500/api/v1/auth/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}'
```

**Response (200):**
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

---

### Ejemplo completo — listar parcelas

```bash
# 1. Login y capturar el token en una variable
TOKEN=$(curl -s -X POST http://localhost:8500/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"tu_password"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['access'])")

# 2. Listar parcelas (respuesta: GeoJSON FeatureCollection paginado)
curl "http://localhost:8500/api/v1/geo_assets/plots/" \
  -H "Authorization: Bearer $TOKEN"
```

**Response (200):**
```json
{
  "count": 3,
  "next": null,
  "previous": null,
  "results": {
    "type": "FeatureCollection",
    "features": [
      {
        "type": "Feature",
        "geometry": {
          "type": "Polygon",
          "coordinates": [[[-109.93, 27.48], [-109.92, 27.48], [-109.92, 27.47], [-109.93, 27.48]]]
        },
        "properties": {
          "id": "550e8400-e29b-41d4-a716-446655440000",
          "code": "PLT-001",
          "ranch": "3f2504e0-...",
          "area_ha": 45.2,
          "perimeter_km": 2.8
        }
      }
    ]
  }
}
```

---

### Errores comunes

Todos los endpoints retornan un `status_code` y un `detail` en la respuesta. Puedes verlos directamente en la terminal donde corre el servidor, en la consola de Django o usando curl para probar la API.

| Codigo | Significado | Solucion |
|---|---|---|
| `401 Unauthorized` | Token ausente, invalido o expirado | Re-login o renovar con `/auth/refresh/` |
| `403 Forbidden` | Tu rol no tiene permiso para esa accion | Verificar nivel de `user_role` requerido |
| `400 Bad Request` | Body con campos invalidos o faltantes | Leer el campo `detail` en la respuesta |
| `404 Not Found` | UUID no existe o no tienes acceso (scope filter) | Verificar que el objeto exista y pertenezca a tu AgroUnit |
| `409 Conflict` | Accion no permitida en el estado actual | Ej: generar reporte en tarea ya cerrada |

---

## Autenticación

Todos los endpoints (excepto login y signup) requieren JWT en el header:

```http
Authorization: Bearer <access_token>
```

| Método | URL | Descripción | Permiso |
|---|---|---|---|
| POST | `/api/v1/auth/login/` | Obtener access + refresh token | Público |
| POST | `/api/v1/auth/refresh/` | Renovar access token | Público |
| POST | `/api/v1/auth/logout/` | Invalidar refresh token | Autenticado |
| POST | `/api/v1/auth/change-password/` | Cambiar contraseña | Autenticado |
| POST | `/api/v1/auth/register/` | Crear usuario (admin crea usuario) | SuperAdmin |
| POST | `/api/v1/auth/signup/` | Registro público sin rol | Público |

---

## API Endpoints

### Usuarios

| Método | URL | Descripción | Permiso |
|---|---|---|---|
| GET | `/api/v1/users/` | Listar usuarios | SuperAdmin |
| GET | `/api/v1/users/me/` | Perfil propio | Autenticado |
| PATCH | `/api/v1/users/me/` | Editar perfil | Autenticado |
| DELETE | `/api/v1/users/<uuid>/` | Soft delete usuario | SuperAdmin |
| GET | `/api/v1/users/roles/` | Listar roles de acceso | Autenticado |
| GET | `/api/v1/users/work-roles/` | Listar roles laborales | Autenticado |
| GET | `/api/v1/users/assignments/` | Listar asignaciones a AgroUnits | Autenticado |
| POST | `/api/v1/users/assignments/create/` | Asignar usuario a AgroUnit | SuperAdmin |
| DELETE | `/api/v1/users/assignments/<id>/delete/` | Remover asignación | SuperAdmin |

### Geografía

| Método | URL | Descripción | Permiso |
|---|---|---|---|
| GET | `/api/v1/geography/countries/` | Listar países | Autenticado |
| GET | `/api/v1/geography/states/` | Listar estados | Autenticado |
| GET | `/api/v1/geography/states/?country=MX` | Filtrar por país (iso_2) | Autenticado |

### Organizaciones

> Multi-tenancy: usuarios sin rol SuperAdmin solo ven las AgroUnits asignadas vía `UserAssignment`.

| Método | URL | Descripción | Permiso |
|---|---|---|---|
| GET | `/api/v1/organizations/` | Listar AgroUnits (scope filter) | Autenticado |
| POST | `/api/v1/organizations/create/` | Crear AgroUnit | SuperAdmin |
| GET | `/api/v1/organizations/<uuid>/` | Detalle AgroUnit | Autenticado |
| PATCH | `/api/v1/organizations/<uuid>/update/` | Actualizar AgroUnit | SuperAdmin |
| DELETE | `/api/v1/organizations/<uuid>/delete/` | Soft delete | SuperAdmin |
| GET | `/api/v1/organizations/agro_sectors/` | Listar sectores | Autenticado |
| POST | `/api/v1/organizations/agro_sectors/create/` | Crear sector | SuperAdmin |
| GET | `/api/v1/organizations/contacts/` | Listar contactos | Autenticado |
| POST | `/api/v1/organizations/contacts/create/` | Crear contacto | Autenticado |
| POST | `/api/v1/organizations/contacts/assign/` | Asignar contacto a AgroUnit | Autenticado |

### Activos geográficos

> Formato GeoJSON Feature en todos los endpoints de Ranch y Plot.
> POST requiere: `{"type": "Feature", "geometry": {...}, "properties": {...}}`
> Las listas devuelven FeatureCollection paginado.

| Método | URL | Descripción | Permiso |
|---|---|---|---|
| GET | `/api/v1/geo_assets/ranches/` | Listar ranchos (scope filter) | Autenticado |
| POST | `/api/v1/geo_assets/ranches/create/` | Crear rancho | SuperAdmin |
| GET | `/api/v1/geo_assets/ranches/<uuid>/` | Detalle rancho | Autenticado |
| PATCH | `/api/v1/geo_assets/ranches/<uuid>/update/` | Actualizar rancho | SuperAdmin |
| DELETE | `/api/v1/geo_assets/ranches/<uuid>/delete/` | Soft delete | SuperAdmin |
| GET | `/api/v1/geo_assets/plots/` | Listar parcelas (scope filter) | Autenticado |
| POST | `/api/v1/geo_assets/plots/create/` | Crear parcela | SuperAdmin |
| GET | `/api/v1/geo_assets/plots/<uuid>/` | Detalle parcela | Autenticado |
| PATCH | `/api/v1/geo_assets/plots/<uuid>/update/` | Actualizar parcela | SuperAdmin |
| DELETE | `/api/v1/geo_assets/plots/<uuid>/delete/` | Soft delete | SuperAdmin |
| GET | `/api/v1/geo_assets/ranch-partners/` | Listar relaciones rancho-socio | Autenticado |
| POST | `/api/v1/geo_assets/ranch-partners/create/` | Crear relación | SuperAdmin |
| DELETE | `/api/v1/geo_assets/ranch-partners/<id>/delete/` | Eliminar relación | SuperAdmin |

### Operaciones de campo

| Método | URL | Descripción | Permiso |
|---|---|---|---|
| GET | `/api/v1/field_ops/crops/` | Listar cultivos (catálogo) | Autenticado |
| POST | `/api/v1/field_ops/crops/create/` | Crear cultivo | SuperAdmin |
| PATCH | `/api/v1/field_ops/crops/<id>/update/` | Actualizar cultivo | SuperAdmin |
| GET | `/api/v1/field_ops/pests/` | Listar plagas (catálogo) | Autenticado |
| POST | `/api/v1/field_ops/pests/create/` | Crear plaga | SuperAdmin |
| PATCH | `/api/v1/field_ops/pests/<id>/update/` | Actualizar plaga | SuperAdmin |
| GET | `/api/v1/field_ops/tasks/` | Listar tareas de campo | Autenticado |
| POST | `/api/v1/field_ops/tasks/create/` | Crear tarea | Técnico+ |
| GET | `/api/v1/field_ops/tasks/<uuid>/` | Detalle tarea | Autenticado |
| PATCH | `/api/v1/field_ops/tasks/<uuid>/update/` | Actualizar tarea | Técnico+ |
| POST | `/api/v1/field_ops/tasks/<uuid>/generate-report/` | Generar/actualizar reporte | Técnico+ |

### DataLayers (motor de captura JSONB)

> Los DataLayerPoints se importan masivamente via CSV (Celery async).
> El campo `parameters` es JSONB con esquema dinámico definido en el DataLayer.

| Método | URL | Descripción | Permiso |
|---|---|---|---|
| GET | `/api/v1/datalayers/` | Listar DataLayers | Autenticado |
| POST | `/api/v1/datalayers/create/` | Crear DataLayer | SuperAdmin |
| GET | `/api/v1/datalayers/<id>/` | Detalle DataLayer | Autenticado |
| PATCH | `/api/v1/datalayers/<id>/update/` | Actualizar DataLayer | SuperAdmin |
| GET | `/api/v1/datalayers/headers/` | Listar headers | Autenticado |
| POST | `/api/v1/datalayers/headers/create/` | Crear header | Técnico+ |
| POST | `/api/v1/datalayers/headers/import/` | Importar CSV masivo (async) | Técnico+ |
| GET | `/api/v1/datalayers/headers/<uuid>/` | Detalle header | Autenticado |
| GET | `/api/v1/datalayers/points/` | Listar puntos (filtros JSONB) | Autenticado |
| POST | `/api/v1/datalayers/points/create/` | Crear punto individual | Técnico+ |
| GET | `/api/v1/datalayers/points/<uuid>/` | Detalle punto | Autenticado |
| GET | `/api/v1/datalayers/points/export/` | Exportar puntos a CSV | Autenticado |

**Filtros disponibles en `/points/`:**

| Parámetro | Tipo | Descripción |
|---|---|---|
| `header` | UUID | Filtrar por header |
| `plot` | UUID | Filtrar por parcela |
| `attribute` | string | Solo puntos que tengan esa clave en `parameters` |
| `captured_after` | ISO 8601 | Desde fecha |
| `captured_before` | ISO 8601 | Hasta fecha |

**Body para crear un punto (GeoJSON Feature):**
```json
{
  "type": "Feature",
  "geometry": {"type": "Point", "coordinates": [-109.93, 27.48]},
  "properties": {
    "header": "<uuid>",
    "captured_at": "2024-03-15T08:30:00Z",
    "parameters": {"pH": 6.8, "N_ppm": 220, "Azufre": 14.5}
  }
}
```

### Archivos adjuntos

> Adjuntos genéricos vinculados a cualquier entidad del sistema (Ranch, Plot, FieldTask, etc.)
> via GenericForeignKey. Los archivos se almacenan en `MEDIA_ROOT/attachments/`.

| Método | URL | Descripción | Permiso |
|---|---|---|---|
| GET | `/api/v1/core/attachments/` | Listar adjuntos (filtrar por model_name + object_id) | Autenticado |
| POST | `/api/v1/core/attachments/` | Subir archivo (multipart/form-data) | Técnico+ |
| DELETE | `/api/v1/core/attachments/<id>/` | Eliminar archivo | Técnico+ |

**Upload de archivo:**
```bash
curl -X POST http://localhost:8500/api/v1/core/attachments/ \
  -H "Authorization: Bearer <token>" \
  -F "model_name=ranch" \
  -F "object_id=<ranch-uuid>" \
  -F "file=@documento.pdf"
```

---

## Roles de acceso (RBAC)

| Nivel | Rol | Capacidades |
|---|---|---|
| 5 | SuperAdmin | Acceso completo al sistema |
| 4 | Gerente | Gestión de productores y usuarios de sus AgroUnits |
| 3 | Supervisor | Lectura, actualización, validación de reportes |
| 2 | Technician | Captura de campo, carga masiva de CSVs |
| 1 | Guest | Solo consulta de reportes |

Los endpoints marcados como "Técnico+" requieren nivel 2 o superior.

---

## Estructura del proyecto

```
CIAgro_alpha/
├── config/
│   ├── settings/
│   │   ├── base.py        # Configuración común (BD, apps, Celery, Spectacular)
│   │   ├── dev.py         # Entorno local (DEBUG=True, rutas GDAL Conda)
│   │   └── prod.py        # Producción (pendiente — Fase F)
│   ├── urls.py            # Registro de todas las URLs por app
│   └── celery.py          # Configuración de Celery
├── apps/
│   ├── core/              # BaseAuditModel, Attachment, AdditionalParamsWidget
│   ├── users/             # Auth JWT, UserRole RBAC, Individual, UserAssignment
│   ├── geography/         # Country, State, seed_geography command
│   ├── organizations/     # AgroUnit, AgroSector, Contact, multi-tenancy
│   ├── geo_assets/        # Ranch, Plot (PostGIS), RanchPartner, LeafletWidget
│   ├── field_ops/         # CropCatalog, PestCatalog, FieldTask, FieldTaskReport
│   └── datalayers/        # DataLayer, DataLayerHeader, DataLayerPoints (JSONB+GIS)
├── logs/
│   ├── development.md     # Bitácora de desarrollo (Resumen de pasos de desarrollo completados)
│   └── dev_log.csv        # Log CSV de pasos completados (Registros de desarrollo)
├── .context/
│   ├── ciagro_valpha.dbml # Esquema de BD (fuente de verdad de modelos)
│   └── roadmap.md         # Fases y progreso
├── docker-compose.yml     # Redis (dev) — full stack (en Fase de desarrollo, no implementado)
├── requirements.txt
└── manage.py
```

---

## Decisiones de arquitectura relevantes

**JSONB para `parameters` en DataLayerPoints:** cada tipo de análisis (suelo, foliar, agua)
tiene atributos distintos definidos en `DataLayer.definition_scheme`. JSONB permite esquemas
dinámicos sin migraciones por cada nuevo tipo de análisis, con índice GIN para búsquedas
eficientes por clave (`parameters ? 'pH'`).

**Celery para importación masiva:** los CSVs de campo pueden contener 60k+ puntos.
La importación es asíncrona con `bulk_create` en batches de 500 para no bloquear el servidor.

**UUID como PK en entidades operativas:** `FieldTask`, `DataLayerHeader`, `DataLayerPoints`
usan UUID v4 para evitar enumeración y facilitar federación futura. Catálogos y entidades
organizacionales usan AutoField (int).

**Soft delete via `BaseAuditModel`:** todas las entidades tienen `is_deleted` + `deleted_at`
+ `deleted_by`. Los soft-deleted no aparecen en querysets por defecto.
