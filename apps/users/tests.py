from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase


from apps.users.models import Individual, User, UserRole, WorkRole

def make_user(username, email, password, role=None, with_individual=True):
    """
    Helper: crea user + individual en una sola llamada.
    """
    user = User.objects.create_user(
        username=username, 
        email=email, 
        password=password, 
        user_role=role
    )
    
    if with_individual:
        Individual.objects.create(
            user=user,
            first_name="Juan",
            last_name="Perez",
            phone="123456789"
        )

    return user

class AuthLoginTests(APITestCase):
    """
    Pruebas de login - POST /api/v1/auth/login
    """
    def setUp(self):
        self.url = reverse("users:auth_login")
        self.user = make_user("testuser", "test@example.com", "test1234")
        
    def test_login_correcto(self):
        res = self.client.post(self.url, {"username": "testuser", "password": "test1234"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)
        self.assertIn("refresh", res.data)
        
    def test_login_password_incorrecto(self):
        res = self.client.post(self.url, {"username": "testuser", "password": "incorrecto"})
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        
    def test_login_usuario_no_existe(self):
        res = self.client.post(self.url, {"username": "noexiste", "password": "test1234"})
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        

class AuthLogoutTests(APITestCase):
    """
    Pruebas de logout - POST /api/v1/auth/logout
    """
    def setUp(self):
        self.user = make_user("logoutuser", "logout@example.com", "test1234")
        login = self.client.post(reverse("users:auth_login"), 
                            {"username": "logoutuser", 
                            "password": "test1234"})
        self.access = login.data["access"]
        self.refresh = login.data["refresh"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")
        
        
    def test_logout_exitoso(self):
        res = self.client.post(reverse("users:auth_logout"), {"refresh": self.refresh})
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        
    def test_logout_sin_auth(self):
        self.client.credentials()
        res = self.client.post(reverse("users:auth_logout"), {"refresh": self.refresh})
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        
    def test_cambio_password_correcto(self):
        res = self.client.post(reverse("users:auth_change_password"), 
                            {"old_password": "test1234", 
                            "new_password": "nuevotest1234"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        
    def test_cambio_password_incorrecto(self):
        res = self.client.post(reverse("users:auth_change_password"), 
                            {"old_password": "incorrecto", 
                            "new_password": "nuevotest1234"})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        
        
class RegisterTests(APITestCase):
    """
    Pruebas de registro - POST /api/v1/auth/register y /api/v1/auth/signup
    """

    def setUp(self):
        self.role_admin = UserRole.objects.create(role_name="SuperAdmin", level=5)
        self.admin = make_user("admin", "admin@example.com", "test1234", self.role_admin)
        login = self.client.post(reverse("users:auth_login"),
                            {"username": "admin",
                            "password": "test1234"})
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    def test_admin_registro_usuario(self):
        res = self.client.post(reverse("users:auth_admin_register"), {
            "username": "nuevo",
            "email": "nuevo@example.com",
            "password": "test1234",
            "first_name": "Anita",
            "last_name": "Huerfanita"
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username="nuevo").exists())
        
    def test_admin_registro_sin_firstname(self):
        res = self.client.post(reverse("users:auth_admin_register"), {
            "username": "sinfirstname",
            "email": "sinfirstname@example.com",
            "password": "test1234",
            "last_name": "SinNombre"
        })
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        
    def test_signup_publico(self):
        self.client.credentials() # sin autenticacion
        res = self.client.post(reverse("users:auth_public_register"), { 
            "username": "publico",
            "email": "publico@example.com",
            "password": "test1234",
            "first_name": "Pluvius",
            "last_name": "Flavius"
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED) # 201: creado
        user = User.objects.get(username="publico") # user guarda el objeto creado
        self.assertFalse(user.user_role) # indicaa que no tiene rol
        
    def test_signup_correo_duplicado(self):
        self.client.credentials() # sin autenticacion
        self.client.post(reverse("users:auth_public_register"), {
            "username": "duplicos",
            "email": "duplicos@example.com",
            "password": "test1234",
            "first_name": "Partos",
            "last_name": "Maquiavelicus"
        })
        res = self.client.post(reverse("users:auth_public_register"), {
            "username": "duplicos",
            "email": "duplicos@example.com",
            "password": "test1234",
            "first_name": "Macarius",
            "last_name": "Maquiavelicus"
        })
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class PermissionTests(APITestCase):
    """GET /api/v1/users/ — control de acceso por nivel de rol"""

    def setUp(self):
        self.url = reverse("users:user_list")
        self.role_admin = UserRole.objects.create(role_name="SuperAdmin", level=5)
        self.role_tech = UserRole.objects.create(role_name="Technician", level=2)
        self.admin = make_user("admin", "admin@example.com", "test1234", role=self.role_admin)
        self.tech = make_user("tech", "tech@example.com", "test1234", role=self.role_tech)

    def _login(self, username):
        res = self.client.post(reverse("users:auth_login"), {
            "username": username, "password": "test1234"
        })
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")

    def test_sin_autenticacion(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_rol_insuficiente(self):
        self._login("tech")
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_superadmin_accede(self):
        self._login("admin")
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)


class UserMeTests(APITestCase):
    """GET y PATCH /api/v1/users/me/"""

    def setUp(self):
        self.url = reverse("users:user_me")
        self.user = make_user("meuser", "me@example.com", "test1234")
        login = self.client.post(reverse("users:auth_login"), {
            "username": "meuser", "password": "test1234"
        })
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

    def test_get_perfil(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["username"], "meuser")
        self.assertIn("individual", res.data)

    def test_patch_individual(self):
        res = self.client.patch(self.url, {"phone": "4491234567"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["phone"], "4491234567")

    def test_me_sin_autenticacion(self):
        self.client.credentials()
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class UserSoftDeleteTests(APITestCase):
    """
    DELETE /api/v1/users/<uuid:pk>/
    Verifica comportamiento de soft delete en usuarios.
    """

    def setUp(self):
        self.role_admin = UserRole.objects.create(role_name="SuperAdmin", level=5)
        self.admin = make_user("admin", "admin@example.com", "test1234", role=self.role_admin)
        self.target = make_user("target", "target@example.com", "test1234")
        login = self.client.post(reverse("users:auth_login"), {
            "username": "admin", "password": "test1234"
        })
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        self.url = reverse("users:user_destroy", kwargs={"pk": self.target.pk})

    def test_delete_retorna_204(self):
        res = self.client.delete(self.url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

    def test_registro_permanece_en_bd(self):
        self.client.delete(self.url)
        self.assertTrue(User.objects.filter(pk=self.target.pk).exists())

    def test_is_deleted_es_true(self):
        self.client.delete(self.url)
        self.target.refresh_from_db()
        self.assertTrue(self.target.is_deleted)

    def test_deleted_at_registrado(self):
        self.client.delete(self.url)
        self.target.refresh_from_db()
        self.assertIsNotNone(self.target.deleted_at)

    def test_deleted_by_es_el_admin(self):
        self.client.delete(self.url)
        self.target.refresh_from_db()
        self.assertEqual(self.target.deleted_by, self.admin)

    def test_usuario_borrado_no_aparece_en_listado(self):
        self.client.delete(self.url)
        res = self.client.get(reverse("users:user_list"))
        usernames = [u["username"] for u in res.data["results"]]
        self.assertNotIn("target", usernames)

    def test_segundo_delete_retorna_404(self):
        self.client.delete(self.url)
        res = self.client.delete(self.url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_sin_permiso_retorna_403(self):
        role_tech = UserRole.objects.create(role_name="Technician", level=2)
        tech = make_user("tech", "tech@example.com", "test1234", role=role_tech)
        login = self.client.post(reverse("users:auth_login"), {
            "username": "tech", "password": "test1234"
        })
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")
        res = self.client.delete(self.url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
