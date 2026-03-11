# apps/datalayers/tests.py
import csv
import tempfile
import uuid
import time
import random
from datetime import date
from pathlib import Path
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.gis.geos import Point

from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.exceptions import ValidationError

from apps.users.models import User, UserRole, UserAssignment
from apps.organizations.models import AgroUnit
from apps.geo_assets.models import Ranch, Plot
from apps.field_ops.models import CropCatalog, FieldTask, FieldTaskReport
from apps.datalayers.models import DataLayer, DataLayerHeader, DataLayerPoints
from apps.datalayers.validators import validate_raw_data_against_scheme


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_role(name, level):
    return UserRole.objects.create(role_name=name, level=level)


def make_user(username, email, password="test1234", role=None):
    return User.objects.create_user(
        username=username, email=email, password=password, user_role=role
    )


def make_agro_unit(code, commercial_name="Test Unit"):
    return AgroUnit.objects.create(code=code, commercial_name=commercial_name)


def make_ranch(code, name="Rancho Test", agro_unit=None):
    return Ranch.objects.create(code=code, name=name, producer=agro_unit)


def make_plot(code, ranch):
    return Plot.objects.create(code=code, ranch=ranch)


def make_crop(name="Maiz", **kwargs):
    return CropCatalog.objects.create(name=name, **kwargs)


def make_datalayer(code="DL-001", name="Test DataLayer", definition_scheme=None):
    return DataLayer.objects.create(
        code=code,
        name=name,
        definition_scheme=definition_scheme or {},
    )


def make_task(agro_unit=None, crop=None, plot=None, task_status="pending", **kwargs):
    """
    Usa 'task_status' en lugar de 'status' para evitar sombrear el módulo
    rest_framework.status importado en el módulo. Se pasa como status= al ORM.
    """
    kwargs.setdefault("title", "Test Task")
    return FieldTask.objects.create(
        agro_unit=agro_unit,
        crop=crop,
        plot=plot,
        status=task_status,
        **kwargs,
    )


def make_header(task=None, datalayer=None, crop=None, plot=None, import_date=None):
    if import_date is None:
        import_date = date.today()
    return DataLayerHeader.objects.create(
        task=task,
        datalayer=datalayer,
        crop=crop,
        plot=plot,
        import_date=import_date,
    )


def make_point(header, geom=None, parameters=None, plot_id=None):
    """
    Crea un DataLayerPoints vía save() para activar la denormalización.
    Si plot_id no es None, lo asigna ANTES de save() para no ser sobreescrito.
    """
    if geom is None:
        geom = Point(-102.29, 21.88, srid=4326)
    if parameters is None:
        parameters = {}
    point = DataLayerPoints(header=header, geom=geom, parameters=parameters)
    if plot_id is not None:
        point.plot_id = plot_id
    point.save()
    return point


def assign_user(user, agro_unit):
    return UserAssignment.objects.create(user=user, agro_unit=agro_unit)


def do_login(client, username, password="test1234"):
    res = client.post(
        reverse("users:auth_login"),
        {"username": username, "password": password},
    )
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
    return res


def make_csv(content=None):
    if content is None:
        content = b"lat,lon,captured_at,ph,mo\n21.88,-102.29,2024-01-15T08:00:00,6.5,2.3\n"
    return SimpleUploadedFile("test.csv", content, content_type="text/csv")


# ---------------------------------------------------------------------------
# 1. ValidatorTests — Pruebas unitarias puras (sin BD)
# ---------------------------------------------------------------------------

class ValidatorTests(TestCase):
    """
    Pruebas unitarias de validate_raw_data_against_scheme().
    No toca la base de datos: son pruebas puras de lógica Python.
    """

    def test_sin_scheme_pasa(self):
        """Si definition_scheme es None, no debe lanzar excepción."""
        validate_raw_data_against_scheme({"ph": 6.5}, None)

    def test_scheme_vacio_pasa(self):
        """Si definition_scheme es {}, no hay campos required → pasa."""
        validate_raw_data_against_scheme({"ph": 6.5}, {})

    def test_sin_required_en_scheme_pasa(self):
        """Si no hay clave 'required' en el scheme, pasa."""
        validate_raw_data_against_scheme({"ph": 6.5}, {"optional": ["mo"]})

    def test_campo_requerido_presente_pasa(self):
        """Si todos los campos requeridos están en raw_data, pasa."""
        scheme = {"required": ["ph", "mo"]}
        validate_raw_data_against_scheme({"ph": 6.5, "mo": 2.3}, scheme)

    def test_campo_requerido_faltante_lanza_error(self):
        """Si falta un campo requerido, debe lanzar ValidationError."""
        scheme = {"required": ["ph", "mo"]}
        with self.assertRaises(ValidationError):
            validate_raw_data_against_scheme({"ph": 6.5}, scheme)

    def test_alias_resuelto_como_valido(self):
        """Un alias del campo requerido debe ser aceptado como válido."""
        scheme = {
            "required": ["ph"],
            "aliases": {"ph": ["pH", "PH"]},
        }
        # "pH" es alias de "ph" → debe pasar sin excepción
        validate_raw_data_against_scheme({"pH": 6.5}, scheme)

    def test_error_enumera_todos_los_campos_faltantes(self):
        """El mensaje de error debe mencionar cada campo faltante."""
        scheme = {"required": ["ph", "mo", "n"]}
        with self.assertRaises(ValidationError) as ctx:
            validate_raw_data_against_scheme({}, scheme)
        detail = str(ctx.exception.detail)
        self.assertIn("ph", detail)
        self.assertIn("mo", detail)
        self.assertIn("n", detail)


# ---------------------------------------------------------------------------
# 2. DataLayerHeaderDenormalizationTests
# ---------------------------------------------------------------------------

class DataLayerHeaderDenormalizationTests(TestCase):
    """
    Verifica que DataLayerHeader.save() hereda plot_id desde task.plot
    cuando el header no lo recibe explícitamente.
    """

    def setUp(self):
        self.unit = make_agro_unit("AU-001")
        self.ranch = make_ranch("RC-001", agro_unit=self.unit)
        self.plot = make_plot("PLT-001", ranch=self.ranch)
        self.crop = make_crop("Maiz")
        self.dl = make_datalayer("DL-001")
        self.task = make_task(
            agro_unit=self.unit,
            crop=self.crop,
            plot=self.plot,
            task_status="open",
        )

    def test_plot_heredado_de_task(self):
        """Si task tiene plot y el header no lo recibe, se debe heredar."""
        header = make_header(
            task=self.task,
            datalayer=self.dl,
            crop=self.crop,
            plot=None,
        )
        header.refresh_from_db()
        self.assertEqual(header.plot_id, self.plot.pk)

    def test_plot_explicito_no_se_sobreescribe(self):
        """Si el header recibe un plot explícito, debe conservarlo."""
        otro_ranch = make_ranch("RC-002", agro_unit=self.unit)
        otro_plot = make_plot("PLT-002", ranch=otro_ranch)
        header = make_header(
            task=self.task,
            datalayer=self.dl,
            crop=self.crop,
            plot=otro_plot,
        )
        header.refresh_from_db()
        self.assertEqual(header.plot_id, otro_plot.pk)

    def test_sin_task_plot_queda_none(self):
        """Sin task vinculada, el plot del header debe permanecer None."""
        header = make_header(
            task=None,
            datalayer=self.dl,
            crop=self.crop,
            plot=None,
        )
        header.refresh_from_db()
        self.assertIsNone(header.plot_id)


# ---------------------------------------------------------------------------
# 3. DataLayerPointsDenormalizationTests
# ---------------------------------------------------------------------------

class DataLayerPointsDenormalizationTests(TestCase):
    """
    Verifica que DataLayerPoints.save() hereda plot_id desde header.plot.
    """

    def setUp(self):
        self.unit = make_agro_unit("AU-001")
        self.ranch = make_ranch("RC-001", agro_unit=self.unit)
        self.plot = make_plot("PLT-001", ranch=self.ranch)
        self.crop = make_crop("Maiz")
        self.dl = make_datalayer("DL-001")
        self.header = make_header(
            datalayer=self.dl,
            crop=self.crop,
            plot=self.plot,
        )

    def test_plot_heredado_de_header(self):
        """El punto debe heredar plot_id del header al hacer save()."""
        point = make_point(header=self.header)
        self.assertEqual(point.plot_id, self.plot.pk)

    def test_plot_id_explicito_no_se_sobreescribe(self):
        """Si plot_id se asigna antes de save(), no se sobreescribe con None."""
        otro_ranch = make_ranch("RC-002", agro_unit=self.unit)
        otro_plot = make_plot("PLT-002", ranch=otro_ranch)
        point = make_point(header=self.header, plot_id=otro_plot.pk)
        self.assertEqual(point.plot_id, otro_plot.pk)


# ---------------------------------------------------------------------------
# 4. DataLayerAPITests
# ---------------------------------------------------------------------------

class DataLayerAPITests(APITestCase):
    """
    GET  /api/v1/datalayers/              → IsAuthenticated
    POST /api/v1/datalayers/create/       → IsSuperAdmin (level>=5)
    GET  /api/v1/datalayers/<pk>/         → IsAuthenticated
    PATCH /api/v1/datalayers/<pk>/update/ → IsSuperAdmin
    """

    def setUp(self):
        self.role_admin = make_role("SuperAdmin", 5)
        self.role_guest = make_role("Guest", 1)
        self.admin = make_user("admin", "admin@ex.com", role=self.role_admin)
        self.guest = make_user("guest", "guest@ex.com", role=self.role_guest)
        self.dl = make_datalayer("DL-001", "Muestreo Suelo")

    def test_list_autenticado_retorna_200(self):
        do_login(self.client, "guest")
        res = self.client.get(reverse("datalayers:datalayer-list"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_list_sin_auth_retorna_401(self):
        res = self.client.get(reverse("datalayers:datalayer-list"))
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_superadmin_crea_datalayer(self):
        do_login(self.client, "admin")
        data = {"code": "DL-002", "name": "Mapa Rendimiento"}
        res = self.client.post(reverse("datalayers:datalayer-create"), data)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(DataLayer.objects.filter(code="DL-002").exists())

    def test_guest_no_puede_crear_datalayer(self):
        do_login(self.client, "guest")
        data = {"code": "DL-003", "name": "Intento fallido"}
        res = self.client.post(reverse("datalayers:datalayer-create"), data)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_detail_autenticado_retorna_200(self):
        do_login(self.client, "guest")
        url = reverse("datalayers:datalayer-detail", kwargs={"pk": self.dl.pk})
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["code"], "DL-001")

    def test_superadmin_actualiza_datalayer(self):
        do_login(self.client, "admin")
        url = reverse("datalayers:datalayer-update", kwargs={"pk": self.dl.pk})
        res = self.client.patch(url, {"description": "Análisis de suelo"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.dl.refresh_from_db()
        self.assertEqual(self.dl.description, "Análisis de suelo")


# ---------------------------------------------------------------------------
# 5. DataLayerHeaderAPITests
# ---------------------------------------------------------------------------

class DataLayerHeaderAPITests(APITestCase):
    """
    GET  /api/v1/datalayers/headers/                   → IsAuthenticated
    POST /api/v1/datalayers/headers/create/            → IsTechnician (level>=2)
    GET  /api/v1/datalayers/headers/<uuid:pk>/         → IsAuthenticated
    PATCH /api/v1/datalayers/headers/<uuid:pk>/update/ → IsSupervisor (level>=3)
    """

    def setUp(self):
        self.role_admin = make_role("SuperAdmin", 5)
        self.role_tech = make_role("Technician", 2)
        self.role_guest = make_role("Guest", 1)
        self.admin = make_user("admin", "admin@ex.com", role=self.role_admin)
        self.tech = make_user("tech", "tech@ex.com", role=self.role_tech)
        self.guest = make_user("guest", "guest@ex.com", role=self.role_guest)

        self.unit = make_agro_unit("AU-001")
        self.ranch = make_ranch("RC-001", agro_unit=self.unit)
        self.plot = make_plot("PLT-001", ranch=self.ranch)
        self.crop = make_crop("Maiz")
        self.dl = make_datalayer("DL-001")
        self.task = make_task(
            agro_unit=self.unit,
            crop=self.crop,
            plot=self.plot,
            task_status="open",
        )
        self.header = make_header(
            task=self.task,
            datalayer=self.dl,
            crop=self.crop,
        )

    def test_list_retorna_200(self):
        do_login(self.client, "guest")
        res = self.client.get(reverse("datalayers:datalayerheader-list"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_technician_crea_header(self):
        do_login(self.client, "tech")
        data = {
            "task": str(self.task.pk),
            "datalayer": self.dl.pk,
            "crop": self.crop.pk,
            "import_date": "2024-06-15",
        }
        res = self.client.post(reverse("datalayers:datalayerheader-create"), data)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_plot_denormalizado_via_api(self):
        """Al crear un header con task, el plot se hereda automáticamente."""
        do_login(self.client, "tech")
        data = {
            "task": str(self.task.pk),
            "datalayer": self.dl.pk,
            "crop": self.crop.pk,
            "import_date": "2024-06-16",
        }
        res = self.client.post(reverse("datalayers:datalayerheader-create"), data)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        header = DataLayerHeader.objects.get(pk=res.data["id"])
        self.assertEqual(header.plot_id, self.plot.pk)

    def test_guest_no_puede_crear_header(self):
        do_login(self.client, "guest")
        data = {
            "datalayer": self.dl.pk,
            "crop": self.crop.pk,
            "import_date": "2024-06-15",
        }
        res = self.client.post(reverse("datalayers:datalayerheader-create"), data)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_detail_retorna_points_count(self):
        """La respuesta de detail debe incluir el conteo correcto de puntos."""
        do_login(self.client, "guest")
        make_point(header=self.header)
        make_point(header=self.header)
        url = reverse("datalayers:datalayerheader-detail", kwargs={"pk": self.header.pk})
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["points_count"], 2)


# ---------------------------------------------------------------------------
# 6. DataLayerPointsAPITests
# ---------------------------------------------------------------------------

class DataLayerPointsAPITests(APITestCase):
    """
    GET  /api/v1/datalayers/points/        → IsAuthenticated (filtro ?header=)
    POST /api/v1/datalayers/points/create/ → IsTechnician (level>=2)
    Valida definition_scheme al crear un punto.
    """

    def setUp(self):
        self.role_tech = make_role("Technician", 2)
        self.role_guest = make_role("Guest", 1)
        self.tech = make_user("tech", "tech@ex.com", role=self.role_tech)
        self.guest = make_user("guest", "guest@ex.com", role=self.role_guest)

        self.unit = make_agro_unit("AU-001")
        self.ranch = make_ranch("RC-001", agro_unit=self.unit)
        self.plot = make_plot("PLT-001", ranch=self.ranch)
        self.crop = make_crop("Maiz")

        scheme = {"required": ["ph", "mo"], "aliases": {"ph": ["pH"]}}
        self.dl = make_datalayer("DL-001", definition_scheme=scheme)
        self.header = make_header(datalayer=self.dl, crop=self.crop, plot=self.plot)
        make_point(header=self.header, parameters={"ph": 6.5, "mo": 2.1})
        make_point(header=self.header, parameters={"ph": 7.0, "mo": 1.8})

    def test_list_retorna_200(self):
        do_login(self.client, "guest")
        res = self.client.get(reverse("datalayers:datalayerpoints-list"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_filtro_por_header(self):
        """?header=<uuid> filtra solo los puntos del header indicado."""
        do_login(self.client, "guest")
        otro_dl = make_datalayer("DL-002")
        otro_header = make_header(datalayer=otro_dl, crop=self.crop)
        make_point(header=otro_header, parameters={"x": 1})

        url = reverse("datalayers:datalayerpoints-list")
        res = self.client.get(url, {"header": str(self.header.pk)})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 2)  # sin paginación — res.data es lista directa

    def test_technician_crea_punto_valido(self):
        """parameters que cumple el definition_scheme → 201 Created."""
        do_login(self.client, "tech")
        data = {
            "header": str(self.header.pk),
            "geom": {"type": "Point", "coordinates": [-102.29, 21.88]},
            "parameters": {"ph": 6.8, "mo": 2.5},
        }
        res = self.client.post(
            reverse("datalayers:datalayerpoints-create"), data, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_parameters_invalido_retorna_400(self):
        """parameters que incumple el definition_scheme → 400 Bad Request."""
        do_login(self.client, "tech")
        data = {
            "header": str(self.header.pk),
            "geom": {"type": "Point", "coordinates": [-102.29, 21.88]},
            "parameters": {"ph": 6.8},  # falta "mo"
        }
        res = self.client.post(
            reverse("datalayers:datalayerpoints-create"), data, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# 7. DataLayerPointsExportViewTests
# ---------------------------------------------------------------------------

class DataLayerPointsExportViewTests(APITestCase):
    """
    Verifica el endpoint GET /api/v1/datalayers/points/export/
    - Devuelve Content-Type text/csv con status 200
    - Las claves del JSONB parameters aparecen como columnas en el header del CSV
    - Un usuario no autenticado recibe 401
    """

    def setUp(self):
        self.role_guest = make_role("Guest", 1)
        self.guest = make_user("guest_exp", "guest_exp@ex.com", role=self.role_guest)

        self.unit  = make_agro_unit("AU-EXP")
        self.ranch = make_ranch("RC-EXP", agro_unit=self.unit)
        self.plot  = make_plot("PLT-EXP", ranch=self.ranch)
        self.crop  = make_crop("Trigo")
        self.dl    = make_datalayer("DL-EXP")
        self.header = make_header(datalayer=self.dl, crop=self.crop, plot=self.plot)

        make_point(header=self.header, parameters={"pH": 6.5, "C": 1.2})
        make_point(header=self.header, parameters={"pH": 7.0, "C": 0.9})

    def test_export_retorna_csv(self):
        """GET export/ con autenticacion → 200 y Content-Type text/csv."""
        do_login(self.client, "guest_exp")
        url = reverse("datalayers:datalayerpoints-export")
        res = self.client.get(url, {"header": str(self.header.pk)})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("text/csv", res["Content-Type"])
        # El CSV debe tener al menos la fila de encabezado + 2 filas de datos
        lines = res.content.decode("utf-8").strip().splitlines()
        self.assertEqual(len(lines), 3)  # header + 2 puntos

    def test_export_columnas_jsonb_aplanadas(self):
        """Las claves de parameters aparecen como columnas en el CSV."""
        do_login(self.client, "guest_exp")
        url = reverse("datalayers:datalayerpoints-export")
        res = self.client.get(url, {"header": str(self.header.pk)})
        primera_linea = res.content.decode("utf-8").splitlines()[0]
        columnas = [c.strip() for c in primera_linea.split(",")]
        self.assertIn("lat",  columnas)
        self.assertIn("lon",  columnas)
        self.assertIn("pH",   columnas)
        self.assertIn("C",    columnas)

    def test_export_sin_autenticacion_retorna_401(self):
        """Sin token → 401 Unauthorized."""
        url = reverse("datalayers:datalayerpoints-export")
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# 8. DataLayerHeaderImportViewTests
# ---------------------------------------------------------------------------

class DataLayerHeaderImportViewTests(APITestCase):
    """
    POST /api/v1/datalayers/headers/import/
    - 400: sin csv_file en el body
    - 409: task con status='closed'
    - 202: importación encolada correctamente (Celery mockeado)
    - 403: usuario con nivel < 2 (Guest)
    """

    def setUp(self):
        self.url = reverse("datalayers:datalayerheader-import")
        self.role_tech = make_role("Technician", 2)
        self.role_guest = make_role("Guest", 1)
        self.tech = make_user("tech", "tech@ex.com", role=self.role_tech)
        self.guest = make_user("guest", "guest@ex.com", role=self.role_guest)

        self.unit = make_agro_unit("AU-001")
        self.ranch = make_ranch("RC-001", agro_unit=self.unit)
        self.plot = make_plot("PLT-001", ranch=self.ranch)
        self.crop = make_crop("Maiz")
        self.dl = make_datalayer("DL-001")
        self.task_open = make_task(
            agro_unit=self.unit,
            crop=self.crop,
            plot=self.plot,
            task_status="open",
        )
        self.task_closed = make_task(
            agro_unit=self.unit,
            crop=self.crop,
            plot=self.plot,
            task_status="closed",
        )

    def test_sin_csv_retorna_400(self):
        do_login(self.client, "tech")
        data = {
            "datalayer": self.dl.pk,
            "crop": self.crop.pk,
            "import_date": "2024-06-15",
        }
        res = self.client.post(self.url, data, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_tarea_cerrada_retorna_409(self):
        do_login(self.client, "tech")
        data = {
            "task": str(self.task_closed.pk),
            "datalayer": self.dl.pk,
            "crop": self.crop.pk,
            "import_date": "2024-06-15",
            "csv_file": make_csv(),
        }
        res = self.client.post(self.url, data, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)

    @patch("apps.datalayers.views.import_csv_to_datalayer.delay")
    def test_importacion_exitosa_retorna_202(self, mock_delay):
        """Con Celery mockeado, crea el header y responde 202 Accepted."""
        mock_delay.return_value.id = "fake-celery-id"
        do_login(self.client, "tech")
        data = {
            "task": str(self.task_open.pk),
            "datalayer": self.dl.pk,
            "crop": self.crop.pk,
            "import_date": "2024-06-15",
            "csv_file": make_csv(),
        }
        res = self.client.post(self.url, data, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn("header_id", res.data)
        self.assertIn("celery_task_id", res.data)
        mock_delay.assert_called_once()

    def test_guest_no_puede_importar(self):
        do_login(self.client, "guest")
        data = {
            "datalayer": self.dl.pk,
            "crop": self.crop.pk,
            "import_date": "2024-06-15",
            "csv_file": make_csv(),
        }
        res = self.client.post(self.url, data, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


# ---------------------------------------------------------------------------
# 8. GenerateReportViewTests
# ---------------------------------------------------------------------------

class GenerateReportViewTests(APITestCase):
    """
    POST /api/v1/field_ops/tasks/<uuid:pk>/generate-report/
    - 201: primera generación (reporte creado)
    - 200: segunda llamada (idempotente, update_or_create)
    - 409: tarea cerrada
    - 404: tarea no existe o fuera de scope
    - Verifica cálculo estadístico en summary_data
    """

    def setUp(self):
        self.role_admin = make_role("SuperAdmin", 5)
        self.admin = make_user("admin", "admin@ex.com", role=self.role_admin)

        self.unit = make_agro_unit("AU-001")
        self.ranch = make_ranch("RC-001", agro_unit=self.unit)
        self.plot = make_plot("PLT-001", ranch=self.ranch)
        self.crop = make_crop("Maiz")
        self.dl = make_datalayer("DL-001")

        self.task = make_task(
            agro_unit=self.unit,
            crop=self.crop,
            plot=self.plot,
            task_status="completed",
        )
        self.header = make_header(
            task=self.task,
            datalayer=self.dl,
            crop=self.crop,
        )
        # 3 puntos con valores conocidos para verificar las estadísticas
        make_point(header=self.header, parameters={"ph": 6.0, "mo": 2.0})
        make_point(header=self.header, parameters={"ph": 7.0, "mo": 3.0})
        make_point(header=self.header, parameters={"ph": 8.0, "mo": 4.0})

        self.url = reverse("field_ops:task-generate-report", kwargs={"pk": self.task.pk})

    def test_primera_generacion_retorna_201(self):
        do_login(self.client, "admin")
        res = self.client.post(self.url)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_segunda_generacion_es_idempotente_retorna_200(self):
        """Llamar dos veces no duplica el reporte (update_or_create)."""
        do_login(self.client, "admin")
        self.client.post(self.url)
        res = self.client.post(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(FieldTaskReport.objects.filter(task=self.task).count(), 1)

    def test_summary_data_calcula_estadisticas_correctas(self):
        """summary_data debe contener total_points y stats por campo numérico."""
        do_login(self.client, "admin")
        res = self.client.post(self.url)
        summary = res.data["summary_data"]
        self.assertEqual(summary["total_points"], 3)
        self.assertIn("ph", summary["fields"])
        ph = summary["fields"]["ph"]
        self.assertEqual(ph["count"], 3)
        self.assertAlmostEqual(ph["avg"], 7.0, places=2)
        self.assertAlmostEqual(ph["min"], 6.0, places=2)
        self.assertAlmostEqual(ph["max"], 8.0, places=2)

    def test_tarea_cerrada_retorna_409(self):
        closed_task = make_task(
            agro_unit=self.unit,
            crop=self.crop,
            task_status="closed",
        )
        do_login(self.client, "admin")
        url = reverse("field_ops:task-generate-report", kwargs={"pk": closed_task.pk})
        res = self.client.post(url)
        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)

    def test_tarea_inexistente_retorna_404(self):
        do_login(self.client, "admin")
        fake_pk = uuid.uuid4()
        url = reverse("field_ops:task-generate-report", kwargs={"pk": fake_pk})
        res = self.client.post(url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)


# ---------------------------------------------------------------------------
# 9. BulkPerformanceTests
# ---------------------------------------------------------------------------

class BulkPerformanceTests(TestCase):
    """
    Verifica que bulk_create de 60,000 DataLayerPoints se complete en < 60s.
    Simula una importación masiva real (ej: mapa de rendimiento).
    Nota: los puntos se crean con plot_id explícito porque bulk_create no
    llama a save(), por lo que la denormalización automática no aplica.
    """

    def setUp(self):
        unit = make_agro_unit("AU-PERF")
        ranch = make_ranch("RC-PERF", agro_unit=unit)
        self.plot = make_plot("PLT-PERF", ranch=ranch)
        crop = make_crop("Maiz Perf")
        dl = make_datalayer("DL-PERF")
        self.header = make_header(datalayer=dl, crop=crop, plot=self.plot)

    def test_bulk_create_60k_puntos_en_menos_de_60s(self):
        N = 60_000
        points = [
            DataLayerPoints(
                header=self.header,
                plot_id=self.plot.pk,
                geom=Point(
                    -102.29 + random.uniform(-0.1, 0.1),
                    21.88 + random.uniform(-0.1, 0.1),
                    srid=4326,
                ),
                parameters={
                    "ph": round(random.uniform(5.0, 8.5), 2),
                    "mo": round(random.uniform(1.0, 5.0), 2),
                },
            )
            for _ in range(N)
        ]
        start = time.time()
        DataLayerPoints.objects.bulk_create(points, batch_size=500)
        elapsed = time.time() - start
        count = DataLayerPoints.objects.filter(header=self.header).count()
        self.assertEqual(count, N)
        self.assertLess(
            elapsed, 60,
            f"bulk_create de {N} puntos tardó {elapsed:.1f}s (límite: 60s)"
        )


# ---------------------------------------------------------------------------
# 10. EndToEndCSVImportTest — Pipeline completo: CSV real → DataLayerPoints
# ---------------------------------------------------------------------------

class EndToEndCSVImportTest(TestCase):
    """
    Test de integración end-to-end que valida el pipeline completo sin mocks:
      1. Crea DataLayer con definition_scheme basado en el CSV real.
      2. Crea DataLayerHeader (metadatos del lote).
      3. Lee el CSV real de disco, renombra longitude→lon / latitude→lat,
         escribe a temp file y llama import_csv_to_datalayer() directamente
         (sin .delay() — Celery sincrónico para tests).
      4. Verifica 440 DataLayerPoints creados con geom y parameters correctos.

    CSV de referencia:
      examples/csvs/Indices_vegetales_Grupo U_Churi_5_2025_IV_2025-10-20.csv
      (440 filas · Grupo U · Churi · Lote 5 · Índices vegetales SENTINEL2)
    """

    EXPECTED_ROWS = 440

    CSV_PATH = (
        Path(__file__).resolve().parents[3]
        / "examples"
        / "csvs"
        / "Indices_vegetales_Grupo U_Churi_5_2025_IV_2025-10-20.csv"
    )

    DEFINITION_SCHEME = {
        "required": [],
        "optional": [
            "id", "polygon_id", "lote", "conjunto_datos", "producto", "id_obj",
            "ndvi", "vigor_nir", "osavi", "vari", "indice_suelo_desnudo",
            "imagen_rojo", "imagen_verde", "imagen_azul", "limite_rojo",
            "swir", "ndre", "msavi2", "gndvi", "ndmi", "psri",
            "fecha_adquisicion", "polygon_code", "created at",
        ],
        "aliases": {},
        "units": {},
    }

    @classmethod
    def setUpTestData(cls):
        role = make_role("Tecnico", 2)
        tech = make_user("tech_churi", "tech@churi.com", role=role)
        agro_unit = make_agro_unit(code="GU", commercial_name="Grupo U")
        assign_user(tech, agro_unit)
        ranch = make_ranch(code="GU-CU8", name="Churi", agro_unit=agro_unit)
        cls.plot = make_plot(code="GU-CU8-P5", ranch=ranch)
        cls.crop = make_crop(name="Índices Vegetales 2025")
        cls.datalayer = make_datalayer(
            code="IV-CHURI-2025",
            name="Índices Vegetales Grupo U Churi 2025",
            definition_scheme=cls.DEFINITION_SCHEME,
        )
        cls.header = make_header(
            datalayer=cls.datalayer,
            plot=cls.plot,
            crop=cls.crop,
            import_date=date(2025, 10, 20),
        )

    def test_full_csv_import_pipeline(self):
        """
        Valida que import_csv_to_datalayer procese el CSV real de índices
        vegetales, creando 440 DataLayerPoints con geom y parameters correctos.
        """
        from apps.datalayers.tasks import import_csv_to_datalayer

        # 1. Leer el CSV real y renombrar columnas de coordenadas
        with open(self.CSV_PATH, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            new_fieldnames = [
                "lon" if col == "longitude" else "lat" if col == "latitude" else col
                for col in reader.fieldnames
            ]
            rows = [
                {new: row[orig] for orig, new in zip(reader.fieldnames, new_fieldnames)}
                for row in reader
            ]

        # 2. Escribir a archivo temporal (la tarea lo elimina en su bloque finally)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, newline="", encoding="utf-8"
        ) as tmp:
            writer = csv.DictWriter(tmp, fieldnames=new_fieldnames)
            writer.writeheader()
            writer.writerows(rows)
            tmp_path = tmp.name

        # 3. Ejecutar la tarea Celery de forma síncrona (sin .delay())
        result = import_csv_to_datalayer(str(self.header.id), tmp_path)

        # 4. Verificar resultado de la tarea
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["created"], self.EXPECTED_ROWS)
        self.assertEqual(result["errors"], [])

        # 5. Verificar puntos en BD
        self.assertEqual(
            DataLayerPoints.objects.filter(header=self.header).count(),
            self.EXPECTED_ROWS,
        )

        # 6. Spot-check: primer punto (id_obj="1")
        point = DataLayerPoints.objects.get(
            header=self.header, parameters__id_obj="1"
        )
        # Coordenadas: lon → geom.x, lat → geom.y (convención GIS)
        self.assertAlmostEqual(point.geom.x, -101.09306745, places=4)
        self.assertAlmostEqual(point.geom.y, 20.53422154, places=4)
        # parameters contiene columnas del CSV (excepto lat/lon, extraídos por la tarea)
        self.assertIn("ndvi", point.parameters)
        self.assertIn("fecha_adquisicion", point.parameters)
        self.assertNotIn("lat", point.parameters)
        self.assertNotIn("lon", point.parameters)
        # Denormalización: plot_id heredado del header (bulk_create no llama save())
        self.assertEqual(point.plot_id, self.plot.id)


# ---------------------------------------------------------------------------
# 11. DataLayerImportTaskTransitionTest — Transición de FieldTask al importar
# ---------------------------------------------------------------------------

class DataLayerImportTaskTransitionTest(TestCase):
    """
    D5: Verifica que import_csv_to_datalayer() transiciona automáticamente el
    FieldTask vinculado de 'open' → 'completed' al finalizar la importación.
    También verifica que un header sin task no lanza excepción.
    """

    def setUp(self):
        self.unit = make_agro_unit("AU-TRANS")
        self.ranch = make_ranch("RC-TRANS", agro_unit=self.unit)
        self.plot = make_plot("PLT-TRANS", ranch=self.ranch)
        self.crop = make_crop("Maiz Trans")
        self.dl = make_datalayer("DL-TRANS")
        self.task = make_task(
            agro_unit=self.unit,
            crop=self.crop,
            plot=self.plot,
            task_status="open",
        )
        self.header = make_header(
            task=self.task,
            datalayer=self.dl,
            crop=self.crop,
        )

    def _write_csv(self, content):
        """Escribe content a un archivo temporal y devuelve la ruta."""
        import tempfile as _tempfile
        f = _tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, newline="", encoding="utf-8"
        )
        f.write(content)
        f.close()
        return f.name

    def test_import_transiciona_task_a_completed(self):
        """
        Al importar un CSV con puntos válidos, el FieldTask vinculado debe
        cambiar su status a 'completed'.
        """
        from apps.datalayers.tasks import import_csv_to_datalayer

        tmp_path = self._write_csv(
            "lat,lon,captured_at,ph,mo\n"
            "21.88,-102.29,2024-01-15T08:00:00,6.5,2.3\n"
        )
        result = import_csv_to_datalayer(str(self.header.id), tmp_path)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["created"], 1)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "completed")

    def test_import_sin_task_no_falla_y_crea_puntos(self):
        """
        Un header sin task asociada debe importar correctamente sin
        lanzar excepción ni intentar transicionar ninguna tarea.
        """
        from apps.datalayers.tasks import import_csv_to_datalayer

        header_sin_task = make_header(
            task=None,
            datalayer=self.dl,
            crop=self.crop,
            plot=self.plot,
        )
        tmp_path = self._write_csv(
            "lat,lon,captured_at,ph\n"
            "21.88,-102.29,2024-01-15T08:00:00,6.5\n"
        )
        result = import_csv_to_datalayer(str(header_sin_task.id), tmp_path)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(
            DataLayerPoints.objects.filter(header=header_sin_task).count(), 1
        )
