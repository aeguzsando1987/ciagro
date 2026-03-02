# apps/field_ops/tests.py
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import User, UserRole, UserAssignment
from apps.organizations.models import AgroUnit
from apps.datalayers.models import DataLayer
from apps.field_ops.models import CropCatalog, PestCatalog, FieldTask


def make_user(username, email, password, role=None):
    return User.objects.create_user(
        username=username, email=email, password=password, user_role=role
    )


def make_crop(name="Maiz", **kwargs):
    return CropCatalog.objects.create(name=name, **kwargs)


def make_pest(name="Gusano Cogollero", crop=None, **kwargs):
    return PestCatalog.objects.create(name=name, default_crop=crop, **kwargs)


def make_agro_unit(code, commercial_name="Test Unit"):
    return AgroUnit.objects.create(code=code, commercial_name=commercial_name)


def make_datalayer(code="DL-001", name="Test DataLayer"):
    return DataLayer.objects.create(code=code, name=name)


def make_task(agro_unit=None, crop=None, status="pending", **kwargs):
    return FieldTask.objects.create(agro_unit=agro_unit, crop=crop, status=status, **kwargs)


def assign_user(user, agro_unit):
    return UserAssignment.objects.create(user=user, agro_unit=agro_unit)


class CropCatalogListTests(APITestCase):
    """
    GET /api/v1/field_ops/crops/
    Cualquier usuario autenticado puede listar.
    """

    def setUp(self):
        self.url = reverse("field_ops:crop-list")
        self.role_guest = UserRole.objects.create(role_name="Guest", level=1)
        self.guest = make_user("guest", "guest@example.com", "test1234", role=self.role_guest)
        make_crop("Maiz")
        make_crop("Sorgo")
        login = self.client.post(reverse("users:auth_login"), {"username": "guest", "password": "test1234"})
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    def test_list_retorna_200(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_list_retorna_todos_los_cultivos(self):
        res = self.client.get(self.url)
        names = [c["name"] for c in res.data["results"]]
        self.assertIn("Maiz", names)
        self.assertIn("Sorgo", names)

    def test_list_sin_auth_retorna_401(self):
        self.client.credentials()
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class CropCatalogCreateTests(APITestCase):
    """
    POST /api/v1/field_ops/crops/create/
    Solo SuperAdmin puede crear.
    """

    def setUp(self):
        self.url = reverse("field_ops:crop-create")
        self.role_admin = UserRole.objects.create(role_name="SuperAdmin", level=5)
        self.role_guest = UserRole.objects.create(role_name="Guest", level=1)
        self.admin = make_user("admin", "admin@example.com", "test1234", role=self.role_admin)
        self.guest = make_user("guest", "guest@example.com", "test1234", role=self.role_guest)

    def _login(self, username):
        res = self.client.post(reverse("users:auth_login"), {"username": username, "password": "test1234"})
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")

    def test_superadmin_crea_cultivo(self):
        self._login("admin")
        res = self.client.post(self.url, {"name": "Frijol"})
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(CropCatalog.objects.filter(name="Frijol").exists())

    def test_guest_no_puede_crear(self):
        self._login("guest")
        res = self.client.post(self.url, {"name": "Frijol"})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_sin_auth_retorna_401(self):
        res = self.client.post(self.url, {"name": "Frijol"})
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_nombre_duplicado_retorna_400(self):
        self._login("admin")
        make_crop("Trigo")
        res = self.client.post(self.url, {"name": "Trigo"})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_sin_nombre_retorna_400(self):
        self._login("admin")
        res = self.client.post(self.url, {"description": "Sin nombre"})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class CropCatalogDetailTests(APITestCase):
    """
    GET  /api/v1/field_ops/crops/<pk>/
    PATCH /api/v1/field_ops/crops/<pk>/update/
    """

    def setUp(self):
        self.role_admin = UserRole.objects.create(role_name="SuperAdmin", level=5)
        self.role_guest = UserRole.objects.create(role_name="Guest", level=1)
        self.admin = make_user("admin", "admin@example.com", "test1234", role=self.role_admin)
        self.guest = make_user("guest", "guest@example.com", "test1234", role=self.role_guest)
        self.crop = make_crop("Cebada")

    def _login(self, username):
        res = self.client.post(reverse("users:auth_login"), {"username": username, "password": "test1234"})
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")

    def test_detail_retorna_200(self):
        self._login("guest")
        url = reverse("field_ops:crop-detail", kwargs={"pk": self.crop.pk})
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["name"], "Cebada")

    def test_detail_sin_auth_retorna_401(self):
        url = reverse("field_ops:crop-detail", kwargs={"pk": self.crop.pk})
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_superadmin_actualiza_cultivo(self):
        self._login("admin")
        url = reverse("field_ops:crop-update", kwargs={"pk": self.crop.pk})
        res = self.client.patch(url, {"description": "Cereal de invierno"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.crop.refresh_from_db()
        self.assertEqual(self.crop.description, "Cereal de invierno")

    def test_guest_no_puede_actualizar(self):
        self._login("guest")
        url = reverse("field_ops:crop-update", kwargs={"pk": self.crop.pk})
        res = self.client.patch(url, {"description": "Intento fallido"})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class PestCatalogListTests(APITestCase):
    """
    GET /api/v1/field_ops/pests/
    Lista plagas. Filtro ?default_crop=<id>.
    """

    def setUp(self):
        self.url = reverse("field_ops:pest-list")
        self.role_guest = UserRole.objects.create(role_name="Guest", level=1)
        self.guest = make_user("guest", "guest@example.com", "test1234", role=self.role_guest)
        self.crop_maiz = make_crop("Maiz")
        self.crop_sorgo = make_crop("Sorgo")
        make_pest("Gusano Cogollero", crop=self.crop_maiz)
        make_pest("Pulgon", crop=self.crop_sorgo)
        make_pest("Araña Roja")  # sin cultivo asociado
        login = self.client.post(reverse("users:auth_login"), {"username": "guest", "password": "test1234"})
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    def test_list_retorna_200(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_list_retorna_todas_las_plagas(self):
        res = self.client.get(self.url)
        self.assertEqual(res.data["count"], 3)

    def test_filtro_por_default_crop(self):
        res = self.client.get(self.url, {"default_crop": self.crop_maiz.pk})
        names = [p["name"] for p in res.data["results"]]
        self.assertIn("Gusano Cogollero", names)
        self.assertNotIn("Pulgon", names)

    def test_filtro_crop_sin_resultados(self):
        otro_crop = make_crop("Trigo")
        res = self.client.get(self.url, {"default_crop": otro_crop.pk})
        self.assertEqual(res.data["count"], 0)

    def test_list_sin_auth_retorna_401(self):
        self.client.credentials()
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PestCatalogCreateTests(APITestCase):
    """
    POST /api/v1/field_ops/pests/create/
    Solo SuperAdmin puede crear. Verifica nested serializer en respuesta GET.
    """

    def setUp(self):
        self.url = reverse("field_ops:pest-create")
        self.role_admin = UserRole.objects.create(role_name="SuperAdmin", level=5)
        self.role_guest = UserRole.objects.create(role_name="Guest", level=1)
        self.admin = make_user("admin", "admin@example.com", "test1234", role=self.role_admin)
        self.guest = make_user("guest", "guest@example.com", "test1234", role=self.role_guest)
        self.crop = make_crop("Maiz")

    def _login(self, username):
        res = self.client.post(reverse("users:auth_login"), {"username": username, "password": "test1234"})
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")

    def test_superadmin_crea_plaga_sin_cultivo(self):
        self._login("admin")
        res = self.client.post(self.url, {"name": "Trips"})
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(PestCatalog.objects.filter(name="Trips").exists())

    def test_superadmin_crea_plaga_con_cultivo(self):
        self._login("admin")
        res = self.client.post(self.url, {"name": "Gusano Cogollero", "default_crop_id": self.crop.pk})
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        plaga = PestCatalog.objects.get(name="Gusano Cogollero")
        self.assertEqual(plaga.default_crop, self.crop)

    def test_guest_no_puede_crear(self):
        self._login("guest")
        res = self.client.post(self.url, {"name": "Trips"})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_nombre_duplicado_retorna_400(self):
        self._login("admin")
        make_pest("Pulgon")
        res = self.client.post(self.url, {"name": "Pulgon"})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_crop_id_invalido_retorna_400(self):
        self._login("admin")
        res = self.client.post(self.url, {"name": "NuevaPlaga", "default_crop_id": 9999})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class PestCatalogDetailTests(APITestCase):
    """
    GET  /api/v1/field_ops/pests/<pk>/
    PATCH /api/v1/field_ops/pests/<pk>/update/
    Verifica que default_crop sea objeto anidado en lectura.
    """

    def setUp(self):
        self.role_admin = UserRole.objects.create(role_name="SuperAdmin", level=5)
        self.role_guest = UserRole.objects.create(role_name="Guest", level=1)
        self.admin = make_user("admin", "admin@example.com", "test1234", role=self.role_admin)
        self.guest = make_user("guest", "guest@example.com", "test1234", role=self.role_guest)
        self.crop = make_crop("Maiz")
        self.pest = make_pest("Gusano Cogollero", crop=self.crop)

    def _login(self, username):
        res = self.client.post(reverse("users:auth_login"), {"username": username, "password": "test1234"})
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")

    def test_detail_retorna_200(self):
        self._login("guest")
        url = reverse("field_ops:pest-detail", kwargs={"pk": self.pest.pk})
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_detail_default_crop_es_objeto_anidado(self):
        """GET debe retornar default_crop como objeto, no como entero."""
        self._login("guest")
        url = reverse("field_ops:pest-detail", kwargs={"pk": self.pest.pk})
        res = self.client.get(url)
        self.assertIsInstance(res.data["default_crop"], dict)
        self.assertEqual(res.data["default_crop"]["name"], "Maiz")

    def test_detail_sin_auth_retorna_401(self):
        url = reverse("field_ops:pest-detail", kwargs={"pk": self.pest.pk})
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_superadmin_actualiza_plaga(self):
        self._login("admin")
        url = reverse("field_ops:pest-update", kwargs={"pk": self.pest.pk})
        res = self.client.patch(url, {"description": "Lepidoptera noctuidae"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.pest.refresh_from_db()
        self.assertEqual(self.pest.description, "Lepidoptera noctuidae")

    def test_superadmin_cambia_default_crop(self):
        self._login("admin")
        otro_crop = make_crop("Sorgo")
        url = reverse("field_ops:pest-update", kwargs={"pk": self.pest.pk})
        res = self.client.patch(url, {"default_crop_id": otro_crop.pk})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.pest.refresh_from_db()
        self.assertEqual(self.pest.default_crop, otro_crop)

    def test_guest_no_puede_actualizar(self):
        self._login("guest")
        url = reverse("field_ops:pest-update", kwargs={"pk": self.pest.pk})
        res = self.client.patch(url, {"description": "Intento fallido"})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class FieldTaskListTests(APITestCase):
    """
    GET /api/v1/field_ops/tasks/
    ScopeFilter: SuperAdmin ve todo; usuario normal solo ve tareas de sus unidades asignadas.
    Filtro opcional ?status=<valor>.
    """

    def setUp(self):
        self.url = reverse("field_ops:task-list")
        self.role_admin = UserRole.objects.create(role_name="SuperAdmin", level=5)
        self.role_guest = UserRole.objects.create(role_name="Guest", level=1)
        self.admin = make_user("admin", "admin@example.com", "test1234", role=self.role_admin)
        self.guest = make_user("guest", "guest@example.com", "test1234", role=self.role_guest)

        self.unit_a = make_agro_unit("AU-001", "Unidad A")
        self.unit_b = make_agro_unit("AU-002", "Unidad B")

        # guest solo asignado a unit_a
        assign_user(self.guest, self.unit_a)

        self.task_a = make_task(agro_unit=self.unit_a, title="Tarea Unidad A")
        self.task_b = make_task(agro_unit=self.unit_b, title="Tarea Unidad B")
        self.task_completed = make_task(agro_unit=self.unit_a, title="Tarea Completada", status="completed")

    def _login(self, username):
        res = self.client.post(reverse("users:auth_login"), {"username": username, "password": "test1234"})
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")

    def test_list_retorna_200(self):
        self._login("admin")
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_superadmin_ve_todas_las_tareas(self):
        self._login("admin")
        res = self.client.get(self.url)
        self.assertEqual(res.data["count"], 3)

    def test_usuario_ve_solo_tareas_de_su_unidad(self):
        """Guest asignado a unit_a solo debe ver las tareas de unit_a."""
        self._login("guest")
        res = self.client.get(self.url)
        titles = [t["title"] for t in res.data["results"]]
        self.assertIn("Tarea Unidad A", titles)
        self.assertIn("Tarea Completada", titles)
        self.assertNotIn("Tarea Unidad B", titles)

    def test_usuario_sin_asignacion_no_ve_tareas(self):
        """Usuario sin ninguna asignación debe recibir lista vacía."""
        guest2 = make_user("guest2", "guest2@example.com", "test1234", role=self.role_guest)
        res = self.client.post(reverse("users:auth_login"), {"username": "guest2", "password": "test1234"})
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
        res = self.client.get(self.url)
        self.assertEqual(res.data["count"], 0)

    def test_filtro_por_status(self):
        self._login("admin")
        res = self.client.get(self.url, {"status": "completed"})
        self.assertEqual(res.data["count"], 1)
        self.assertEqual(res.data["results"][0]["title"], "Tarea Completada")

    def test_list_sin_auth_retorna_401(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class FieldTaskCreateTests(APITestCase):
    """
    POST /api/v1/field_ops/tasks/create/
    Solo SuperAdmin puede crear. Valida RegexValidator en campo cycle.
    """

    def setUp(self):
        self.url = reverse("field_ops:task-create")
        self.role_admin = UserRole.objects.create(role_name="SuperAdmin", level=5)
        self.role_guest = UserRole.objects.create(role_name="Guest", level=1)
        self.admin = make_user("admin", "admin@example.com", "test1234", role=self.role_admin)
        self.guest = make_user("guest", "guest@example.com", "test1234", role=self.role_guest)
        self.unit = make_agro_unit("AU-001", "Unidad Test")
        self.crop = make_crop("Maiz")

    def _login(self, username):
        res = self.client.post(reverse("users:auth_login"), {"username": username, "password": "test1234"})
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")

    def test_superadmin_crea_tarea_minima(self):
        """Solo title es suficiente para crear una tarea."""
        self._login("admin")
        res = self.client.post(self.url, {"title": "Nueva Tarea"})
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(FieldTask.objects.filter(title="Nueva Tarea").exists())

    def test_superadmin_crea_tarea_con_crop_id(self):
        """crop_id (write_only) debe enlazar el cultivo; respuesta incluye crop como objeto."""
        self._login("admin")
        res = self.client.post(self.url, {"title": "Tarea con Cultivo", "crop_id": self.crop.pk})
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        tarea = FieldTask.objects.get(title="Tarea con Cultivo")
        self.assertEqual(tarea.crop, self.crop)

    def test_cycle_formato_valido(self):
        """Ciclo con formato YYYY-A debe aceptarse."""
        self._login("admin")
        res = self.client.post(self.url, {"title": "Ciclo Verano", "cycle": "2024-A"})
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_cycle_formato_invalido_retorna_400(self):
        """Ciclo con formato incorrecto (ej. 2024-X) debe rechazarse."""
        self._login("admin")
        res = self.client.post(self.url, {"title": "Ciclo Malo", "cycle": "2024-X"})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_guest_no_puede_crear(self):
        self._login("guest")
        res = self.client.post(self.url, {"title": "Intento fallido"})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_sin_auth_retorna_401(self):
        res = self.client.post(self.url, {"title": "Sin token"})
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class FieldTaskDetailTests(APITestCase):
    """
    GET  /api/v1/field_ops/tasks/<uuid:pk>/
    PATCH /api/v1/field_ops/tasks/<uuid:pk>/update/
    Verifica: UUID pk en URL, status_display legible, crop anidado, scope 404.
    """

    def setUp(self):
        self.role_admin = UserRole.objects.create(role_name="SuperAdmin", level=5)
        self.role_guest = UserRole.objects.create(role_name="Guest", level=1)
        self.admin = make_user("admin", "admin@example.com", "test1234", role=self.role_admin)
        self.guest = make_user("guest", "guest@example.com", "test1234", role=self.role_guest)

        self.unit = make_agro_unit("AU-001", "Unidad Test")
        assign_user(self.guest, self.unit)

        self.crop = make_crop("Maiz")
        self.datalayer = make_datalayer(code="DL-001", name="Muestreo Suelo")
        self.task = make_task(
            agro_unit=self.unit,
            crop=self.crop,
            title="Tarea de prueba",
            status="pending",
        )
        self.task.datalayer = self.datalayer
        self.task.save()

    def _login(self, username):
        res = self.client.post(reverse("users:auth_login"), {"username": username, "password": "test1234"})
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")

    def test_detail_retorna_200(self):
        self._login("admin")
        url = reverse("field_ops:task-detail", kwargs={"pk": self.task.pk})
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_detail_status_display_es_legible(self):
        """status='pending' debe producir status_display='Pendiente'."""
        self._login("admin")
        url = reverse("field_ops:task-detail", kwargs={"pk": self.task.pk})
        res = self.client.get(url)
        self.assertEqual(res.data["status"], "pending")
        self.assertEqual(res.data["status_display"], "Pendiente")

    def test_detail_crop_es_objeto_anidado(self):
        """GET debe retornar crop como objeto anidado, no como entero."""
        self._login("admin")
        url = reverse("field_ops:task-detail", kwargs={"pk": self.task.pk})
        res = self.client.get(url)
        self.assertIsInstance(res.data["crop"], dict)
        self.assertEqual(res.data["crop"]["name"], "Maiz")

    def test_detail_datalayer_code_retorna_codigo(self):
        """datalayer_code debe retornar el código del DataLayer vinculado."""
        self._login("admin")
        url = reverse("field_ops:task-detail", kwargs={"pk": self.task.pk})
        res = self.client.get(url)
        self.assertEqual(res.data["datalayer_code"], "DL-001")

    def test_usuario_asignado_puede_ver_su_tarea(self):
        """Guest asignado a la unidad de la tarea debe recibir 200."""
        self._login("guest")
        url = reverse("field_ops:task-detail", kwargs={"pk": self.task.pk})
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_usuario_no_asignado_retorna_404(self):
        """Usuario sin asignación a la unidad de la tarea debe recibir 404."""
        guest2 = make_user("guest2", "guest2@example.com", "test1234", role=self.role_guest)
        res = self.client.post(reverse("users:auth_login"), {"username": "guest2", "password": "test1234"})
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
        url = reverse("field_ops:task-detail", kwargs={"pk": self.task.pk})
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_detail_sin_auth_retorna_401(self):
        url = reverse("field_ops:task-detail", kwargs={"pk": self.task.pk})
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_superadmin_actualiza_status(self):
        self._login("admin")
        url = reverse("field_ops:task-update", kwargs={"pk": self.task.pk})
        res = self.client.patch(url, {"status": "completed"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "completed")

    def test_guest_no_puede_actualizar(self):
        self._login("guest")
        url = reverse("field_ops:task-update", kwargs={"pk": self.task.pk})
        res = self.client.patch(url, {"status": "completed"})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
