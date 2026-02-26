from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import User, UserRole, UserAssignment
from apps.organizations.models import AgroUnit
from apps.geo_assets.models import Ranch, Plot, RanchPartner


def make_user(username, email, password, role=None):
    return User.objects.create_user(
        username=username, email=email, password=password, user_role=role
    )


def make_agro_unit(code, commercial_name, unit_type="Productor", **kwargs):
    return AgroUnit.objects.create(
        code=code, commercial_name=commercial_name, unit_type=unit_type, **kwargs
    )


def make_ranch(code, name, producer=None, **kwargs):
    return Ranch.objects.create(code=code, name=name, producer=producer, **kwargs)


def make_plot(code, ranch, **kwargs):
    return Plot.objects.create(code=code, ranch=ranch, **kwargs)


class RanchAPITests(APITestCase):
    """
    Permisos y comportamiento CRUD en Ranch.
    Lista/detalle: cualquier autenticado.
    Crear/editar/borrar: solo SuperAdmin.
    """
    def setUp(self):
        self.role_admin = UserRole.objects.create(role_name="SuperAdmin", level=5)
        self.admin = make_user("admin", "admin@example.com", "test1234", role=self.role_admin)
        self.producer = make_agro_unit("P-001", "Productor Semilla")
        self.ranch = make_ranch("R-001", "Rancho El Fresno", producer=self.producer)

        login = self.client.post(reverse("users:auth_login"), {"username": "admin", "password": "test1234"})
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    def test_list_retorna_200(self):
        res = self.client.get(reverse("geo_assets:ranch-list"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_list_sin_auth_retorna_401(self):
        self.client.credentials()
        res = self.client.get(reverse("geo_assets:ranch-list"))
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_superadmin_retorna_201(self):
        data = {
            "type": "Feature",
            "geometry": None,
            "properties": {"code": "R-002", "name": "Rancho Los Olivos"}
        }
        res = self.client.post(reverse("geo_assets:ranch-create"), data, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_create_no_superadmin_retorna_403(self):
        role_guest = UserRole.objects.create(role_name="Guest", level=1)
        make_user("guest", "guest@example.com", "test1234", role=role_guest)
        login = self.client.post(reverse("users:auth_login"), {"username": "guest", "password": "test1234"})
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        data = {
            "type": "Feature",
            "geometry": None,
            "properties": {"code": "R-X", "name": "Rancho X"}
        }
        res = self.client.post(reverse("geo_assets:ranch-create"), data, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_slug_se_genera_automaticamente(self):
        data = {
            "type": "Feature",
            "geometry": None,
            "properties": {"code": "R-003", "name": "Rancho Los Pinos"}
        }
        res = self.client.post(reverse("geo_assets:ranch-create"), data, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["properties"]["slug"], "rancho-los-pinos")

    def test_delete_retorna_204(self):
        url = reverse("geo_assets:ranch-delete", kwargs={"pk": self.ranch.pk})
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_no_elimina_registro_de_bd(self):
        url = reverse("geo_assets:ranch-delete", kwargs={"pk": self.ranch.pk})
        self.client.delete(url)
        self.assertTrue(Ranch.objects.filter(pk=self.ranch.pk).exists())

    def test_delete_marca_is_deleted(self):
        url = reverse("geo_assets:ranch-delete", kwargs={"pk": self.ranch.pk})
        self.client.delete(url)
        self.ranch.refresh_from_db()
        self.assertTrue(self.ranch.is_deleted)


class RanchScopeFilterTests(APITestCase):
    """
    ScopeFilterMixin en Ranch.
    SuperAdmin ve todos los ranchos.
    Guest solo ve ranchos cuyo producer le esta asignado.
    """
    def setUp(self):
        self.role_admin = UserRole.objects.create(role_name="SuperAdmin", level=5)
        self.role_guest = UserRole.objects.create(role_name="Guest", level=1)
        self.admin = make_user("admin", "admin@example.com", "test1234", role=self.role_admin)
        self.guest = make_user("guest", "guest@example.com", "test1234", role=self.role_guest)

        self.unit_a = make_agro_unit("P-A", "Productora Alpha")
        self.unit_b = make_agro_unit("P-B", "Productora Beta")

        self.ranch_a = make_ranch("R-A", "Rancho Alpha", producer=self.unit_a)
        self.ranch_b = make_ranch("R-B", "Rancho Beta", producer=self.unit_b)

        UserAssignment.objects.create(user=self.guest, agro_unit=self.unit_a)

    def _login(self, username):
        login = self.client.post(
            reverse("users:auth_login"), {"username": username, "password": "test1234"}
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    def test_superadmin_ve_todos_los_ranchos(self):
        self._login("admin")
        res = self.client.get(reverse("geo_assets:ranch-list"))
        codes = [r["properties"]["code"] for r in res.data["results"]["features"]]
        self.assertIn("R-A", codes)
        self.assertIn("R-B", codes)

    def test_guest_solo_ve_sus_ranchos(self):
        self._login("guest")
        res = self.client.get(reverse("geo_assets:ranch-list"))
        codes = [r["properties"]["code"] for r in res.data["results"]["features"]]
        self.assertIn("R-A", codes)
        self.assertNotIn("R-B", codes)

    def test_guest_no_puede_acceder_rancho_de_unidad_no_asignada(self):
        self._login("guest")
        url = reverse("geo_assets:ranch-detail", kwargs={"pk": self.ranch_b.pk})
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)


class PlotAPITests(APITestCase):
    """
    Permisos y comportamiento CRUD en Plot.
    """
    def setUp(self):
        self.role_admin = UserRole.objects.create(role_name="SuperAdmin", level=5)
        self.admin = make_user("admin", "admin@example.com", "test1234", role=self.role_admin)
        self.producer = make_agro_unit("P-001", "Productor Semilla")
        self.ranch = make_ranch("R-001", "Rancho El Fresno", producer=self.producer)
        self.plot = make_plot("PLT-001", ranch=self.ranch)

        login = self.client.post(reverse("users:auth_login"), {"username": "admin", "password": "test1234"})
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    def test_list_retorna_200(self):
        res = self.client.get(reverse("geo_assets:plot-list"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_list_sin_auth_retorna_401(self):
        self.client.credentials()
        res = self.client.get(reverse("geo_assets:plot-list"))
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_superadmin_retorna_201(self):
        data = {
            "type": "Feature",
            "geometry": None,
            "properties": {"code": "PLT-002", "ranch": str(self.ranch.pk)}
        }
        res = self.client.post(reverse("geo_assets:plot-create"), data, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_slug_se_genera_automaticamente(self):
        data = {
            "type": "Feature",
            "geometry": None,
            "properties": {"code": "PLT-SLUG", "ranch": str(self.ranch.pk)}
        }
        res = self.client.post(reverse("geo_assets:plot-create"), data, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["properties"]["slug"], "plt-slug")

    def test_delete_retorna_204(self):
        url = reverse("geo_assets:plot-delete", kwargs={"pk": self.plot.pk})
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_marca_is_deleted(self):
        url = reverse("geo_assets:plot-delete", kwargs={"pk": self.plot.pk})
        self.client.delete(url)
        self.plot.refresh_from_db()
        self.assertTrue(self.plot.is_deleted)


class RanchPartnerAPITests(APITestCase):
    """
    Permisos, validacion de relation_type, filtro por rancho y hard delete.
    """
    def setUp(self):
        self.role_admin = UserRole.objects.create(role_name="SuperAdmin", level=5)
        self.admin = make_user("admin", "admin@example.com", "test1234", role=self.role_admin)

        self.producer = make_agro_unit("P-001", "Productor Central", unit_type="Productor")
        self.lab = make_agro_unit("L-001", "Laboratorio Central", unit_type="Laboratorio")
        self.guild = make_agro_unit("G-001", "Asociacion Central", unit_type="Asociación agrícola")

        self.ranch = make_ranch("R-001", "Rancho El Fresno", producer=self.producer)
        self.partner = RanchPartner.objects.create(
            ranch=self.ranch, partner=self.lab, relation_type="lab"
        )

        login = self.client.post(reverse("users:auth_login"), {"username": "admin", "password": "test1234"})
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    def test_list_retorna_200(self):
        res = self.client.get(reverse("geo_assets:ranch-partner-list"))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_create_tipo_correcto_retorna_201(self):
        data = {
            "ranch": str(self.ranch.pk),
            "partner": str(self.guild.pk),
            "relation_type": "guild"
        }
        res = self.client.post(reverse("geo_assets:ranch-partner-create"), data, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_create_tipo_incorrecto_retorna_400(self):
        # Laboratorio registrado como guild (asociacion) — debe fallar la validacion
        data = {
            "ranch": str(self.ranch.pk),
            "partner": str(self.lab.pk),
            "relation_type": "guild"
        }
        res = self.client.post(reverse("geo_assets:ranch-partner-create"), data, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_filtro_por_rancho(self):
        res = self.client.get(
            reverse("geo_assets:ranch-partner-list"),
            {"ranch": str(self.ranch.pk)}
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 1)

    def test_delete_retorna_204(self):
        url = reverse("geo_assets:ranch-partner-delete", kwargs={"pk": self.partner.pk})
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_elimina_registro_de_bd(self):
        # RanchPartner es pivote puro sin is_deleted — hard delete
        url = reverse("geo_assets:ranch-partner-delete", kwargs={"pk": self.partner.pk})
        self.client.delete(url)
        self.assertFalse(RanchPartner.objects.filter(pk=self.partner.pk).exists())
