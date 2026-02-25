from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import User, UserRole, UserAssignment
from apps.organizations.models import AgroSector, AgroUnit


def make_user(username, email, password, role=None):
    return User.objects.create_user(
        username=username, email=email, password=password, user_role=role
    )


def make_agro_unit(code, commercial_name, **kwargs):
    return AgroUnit.objects.create(code=code, commercial_name=commercial_name, **kwargs)


class AgroSectorAPITests(APITestCase):
    """
    Pruebas de permisos en AgroSector API.
    Lista: cualquier autenticado. Crear/Editar/Borrar: solo SuperAdmin.
    """
    def setUp(self):
        self.role_admin = UserRole.objects.create(role_name="SuperAdmin", level=5)
        self.role_guest = UserRole.objects.create(role_name="Guest", level=1)
        self.admin = make_user("admin", "admin@example.com", "test1234", role=self.role_admin)
        self.guest = make_user("guest", "guest@example.com", "test1234", role=self.role_guest)
        AgroSector.objects.create(sector_name="Granos", scian_code="1111")

        login = self.client.post(reverse("users:auth_login"), {"username": "admin", "password": "test1234"})
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    def test_list_autenticado_retorna_200(self):
        res = self.client.get(reverse("organizations:agro_sector_list"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_list_sin_auth_retorna_401(self):
        self.client.credentials()
        res = self.client.get(reverse("organizations:agro_sector_list"))
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_superadmin_retorna_201(self):
        data = {"sector_name": "Frutales", "scian_code": "2222"}
        res = self.client.post(reverse("organizations:agro_sector_create"), data)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_create_no_superadmin_retorna_403(self):
        login = self.client.post(reverse("users:auth_login"), {"username": "guest", "password": "test1234"})
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        data = {"sector_name": "Frutales", "scian_code": "2222"}
        res = self.client.post(reverse("organizations:agro_sector_create"), data)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AgroUnitAPITests(APITestCase):
    """
    Pruebas CRUD de AgroUnit: permisos, soft delete y slug auto-generado.
    """
    def setUp(self):
        self.role_admin = UserRole.objects.create(role_name="SuperAdmin", level=5)
        self.admin = make_user("admin", "admin@example.com", "test1234", role=self.role_admin)
        self.unit = make_agro_unit("U-001", "Grupo Agricola Norte")

        login = self.client.post(reverse("users:auth_login"), {"username": "admin", "password": "test1234"})
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    def test_list_retorna_200(self):
        res = self.client.get(reverse("organizations:agro_unit_list"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_list_sin_auth_retorna_401(self):
        self.client.credentials()
        res = self.client.get(reverse("organizations:agro_unit_list"))
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_superadmin_retorna_201(self):
        data = {"code": "U-002", "commercial_name": "Rancho Los Olivos"}
        res = self.client.post(reverse("organizations:agro_unit_create"), data)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_create_no_superadmin_retorna_403(self):
        role_guest = UserRole.objects.create(role_name="Guest", level=1)
        make_user("guest", "guest@example.com", "test1234", role=role_guest)
        login = self.client.post(reverse("users:auth_login"), {"username": "guest", "password": "test1234"})
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        res = self.client.post(reverse("organizations:agro_unit_create"), {"code": "U-X", "commercial_name": "X"})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_slug_se_genera_automaticamente(self):
        data = {"code": "U-003", "commercial_name": "Rancho Los Pinos"}
        res = self.client.post(reverse("organizations:agro_unit_create"), data)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["slug"], "rancho-los-pinos")

    def test_delete_retorna_204(self):
        url = reverse("organizations:agro_unit_delete", kwargs={"pk": self.unit.pk})
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_no_elimina_registro_de_bd(self):
        url = reverse("organizations:agro_unit_delete", kwargs={"pk": self.unit.pk})
        self.client.delete(url)
        self.assertTrue(AgroUnit.objects.filter(pk=self.unit.pk).exists())

    def test_delete_marca_is_deleted(self):
        url = reverse("organizations:agro_unit_delete", kwargs={"pk": self.unit.pk})
        self.client.delete(url)
        self.unit.refresh_from_db()
        self.assertTrue(self.unit.is_deleted)


class ScopeFilterTests(APITestCase):
    """
    Pruebas de ScopeFilterMixin.
    SuperAdmin ve todo. Otros roles solo ven sus AgroUnit asignadas.
    """
    def setUp(self):
        self.role_admin = UserRole.objects.create(role_name="SuperAdmin", level=5)
        self.role_guest = UserRole.objects.create(role_name="Guest", level=1)
        self.admin = make_user("admin", "admin@example.com", "test1234", role=self.role_admin)
        self.guest = make_user("guest", "guest@example.com", "test1234", role=self.role_guest)

        self.unit_a = make_agro_unit("U-A", "Unidad Alpha")
        self.unit_b = make_agro_unit("U-B", "Unidad Beta")

        UserAssignment.objects.create(user=self.guest, agro_unit=self.unit_a)

    def _login(self, username):
        login = self.client.post(
            reverse("users:auth_login"), {"username": username, "password": "test1234"}
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    def test_superadmin_ve_todas_las_unidades(self):
        self._login("admin")
        res = self.client.get(reverse("organizations:agro_unit_list"))
        codes = [u["code"] for u in res.data["results"]]
        self.assertIn("U-A", codes)
        self.assertIn("U-B", codes)

    def test_guest_solo_ve_unidades_asignadas(self):
        self._login("guest")
        res = self.client.get(reverse("organizations:agro_unit_list"))
        codes = [u["code"] for u in res.data["results"]]
        self.assertIn("U-A", codes)
        self.assertNotIn("U-B", codes)

    def test_guest_no_puede_acceder_unidad_no_asignada(self):
        self._login("guest")
        url = reverse("organizations:agro_unit_detail", kwargs={"pk": self.unit_b.pk})
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
