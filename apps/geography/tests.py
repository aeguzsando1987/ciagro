from django.db import IntegrityError
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.geography.models import Country, State
from apps.users.models import User


def make_country(name="México", iso_2="MX", iso_3="MEX"):
    return Country.objects.create(name=name, iso_2=iso_2, iso_3=iso_3)


def make_state(country, name="Jalisco", code="JAL"):
    return State.objects.create(country=country, name=name, code=code)


# ──────────────────────────────────────────────────────────
# MODELO
# ──────────────────────────────────────────────────────────

class CountryModelTests(APITestCase):

    def test_crear_country(self):
        country = make_country()
        self.assertEqual(Country.objects.count(), 1)
        self.assertEqual(str(country), "México-(MX)-(MEX)")

    def test_iso2_debe_ser_unico(self):
        make_country()
        with self.assertRaises(IntegrityError):
            make_country(name="Otro País", iso_3="OTR")  # iso_2="MX" repetido

    def test_iso3_debe_ser_unico(self):
        make_country()
        with self.assertRaises(IntegrityError):
            make_country(name="Otro País", iso_2="OP")  # iso_3="MEX" repetido


class StateModelTests(APITestCase):

    def setUp(self):
        self.mexico = make_country()
        self.canada = make_country(name="Canadá", iso_2="CA", iso_3="CAN")

    def test_crear_state(self):
        state = make_state(self.mexico)
        self.assertEqual(State.objects.count(), 1)
        self.assertEqual(str(state), "Jalisco-(JAL)-(MEX)")

    def test_codigo_unico_por_pais(self):
        make_state(self.mexico, code="JAL")
        with self.assertRaises(IntegrityError):
            make_state(self.mexico, name="Jalisco Duplicado", code="JAL")

    def test_mismo_codigo_en_distintos_paises(self):
        """BC puede existir en México Y en Canadá sin conflicto."""
        make_state(self.mexico, name="Baja California", code="BC")
        make_state(self.canada, name="British Columbia", code="BC")
        self.assertEqual(State.objects.filter(code="BC").count(), 2)


# ──────────────────────────────────────────────────────────
# API
# ──────────────────────────────────────────────────────────

class CountryAPITests(APITestCase):

    def setUp(self):
        self.url = reverse("geography:country-list")
        self.user = User.objects.create_user(
            username="geouser", email="geo@example.com", password="test1234"
        )
        make_country()
        make_country(name="España", iso_2="ES", iso_3="ESP")

    def _login(self):
        res = self.client.post(reverse("users:auth_login"), {
            "username": "geouser", "password": "test1234"
        })
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")

    def test_sin_token_retorna_401(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_lista_countries_retorna_200(self):
        self._login()
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_campos_en_respuesta(self):
        self._login()
        res = self.client.get(self.url)
        primer_resultado = res.data["results"][0]
        for campo in ["id", "name", "iso_2", "iso_3"]:
            self.assertIn(campo, primer_resultado)


class StateAPITests(APITestCase):

    def setUp(self):
        self.url = reverse("geography:state-list")
        self.user = User.objects.create_user(
            username="geouser", email="geo@example.com", password="test1234"
        )
        self.mexico = make_country()
        self.espana = make_country(name="España", iso_2="ES", iso_3="ESP")
        make_state(self.mexico, name="Jalisco", code="JAL")
        make_state(self.mexico, name="Aguascalientes", code="AGS")
        make_state(self.espana, name="Madrid", code="MAD")

    def _login(self):
        res = self.client.post(reverse("users:auth_login"), {
            "username": "geouser", "password": "test1234"
        })
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")

    def test_sin_token_retorna_401(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_lista_states_retorna_200(self):
        self._login()
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_filtro_por_pais(self):
        self._login()
        res = self.client.get(self.url, {"country": "MX"})
        self.assertEqual(res.data["count"], 2)

    def test_filtro_lowercase(self):
        """El filtro debe normalizar a mayúsculas internamente."""
        self._login()
        res = self.client.get(self.url, {"country": "mx"})
        self.assertEqual(res.data["count"], 2)

    def test_filtro_pais_no_existe(self):
        self._login()
        res = self.client.get(self.url, {"country": "XX"})
        self.assertEqual(res.data["count"], 0)

    def test_estado_country_es_objeto_anidado(self):
        """StateDetailSerializer debe retornar country como objeto, no como id."""
        self._login()
        res = self.client.get(self.url, {"country": "MX"})
        estado = res.data["results"][0]
        self.assertIn("country", estado)
        self.assertIsInstance(estado["country"], dict)
        self.assertIn("iso_2", estado["country"])
