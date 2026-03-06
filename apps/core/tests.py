from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

from apps.core.models import Attachment
from apps.geo_assets.models import Ranch
from apps.users.models import User, UserRole


def _make_ranch(code="RCH-TEST"):
    return Ranch.objects.create(code=code, name=f"Rancho {code}")


def _make_file(name="doc.pdf"):
    return SimpleUploadedFile(name, b"contenido de prueba", content_type="application/pdf")


class AttachmentSyncTests(TestCase):
    """
    Verifica que Attachment._sync_parent_urls() mantiene sincronizado
    el campo attachments_url del objeto padre tras cada save/delete.
    """

    def test_save_attachment_actualiza_attachments_url(self):
        """Al guardar un Attachment, attachments_url del padre se actualiza."""
        ranch = _make_ranch("RCH-S1")
        att = Attachment.objects.create(
            content_object=ranch,
            file=_make_file("foto.pdf"),
        )
        ranch.refresh_from_db()
        self.assertEqual(len(ranch.attachments_url), 1)
        self.assertIn("attachments/ranch/", ranch.attachments_url[0])

    def test_delete_attachment_elimina_url_de_attachments_url(self):
        """Al borrar el único Attachment, attachments_url queda vacía."""
        ranch = _make_ranch("RCH-D1")
        att = Attachment.objects.create(
            content_object=ranch,
            file=_make_file("plano.pdf"),
        )
        att.delete()
        ranch.refresh_from_db()
        self.assertEqual(ranch.attachments_url, [])

    def test_objeto_sin_attachments_url_no_falla(self):
        """
        Si el objeto padre no tiene campo attachments_url,
        _sync_parent_urls() debe retornar silenciosamente sin error.
        User no tiene attachments_url — lo usamos como objeto padre.
        """
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create_user(username="att_test_user", password="pw")
        att = Attachment(content_object=user, file=_make_file("misc.pdf"))
        # No debe lanzar excepción aunque el objeto padre no tenga attachments_url
        att.save()

    def test_multiples_attachments_generan_lista_completa(self):
        """Dos adjuntos al mismo objeto generan una lista con dos URLs."""
        ranch = _make_ranch("RCH-M1")
        Attachment.objects.create(content_object=ranch, file=_make_file("a.pdf"))
        Attachment.objects.create(content_object=ranch, file=_make_file("b.pdf"))
        ranch.refresh_from_db()
        self.assertEqual(len(ranch.attachments_url), 2)
        urls = ranch.attachments_url
        self.assertTrue(all(u.startswith(settings.MEDIA_URL) for u in urls))


class AttachmentAPITests(APITestCase):
    """Tests para los endpoints REST de Attachment (upload / list / delete)."""

    def setUp(self):
        role = UserRole.objects.create(role_name="Technician", level=2)
        self.user = User.objects.create_user(
            username="api_tech_attach", password="pw", user_role=role
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.ranch = Ranch.objects.create(code="RCH-API1", name="Rancho API")
        self.list_url = reverse("core:attachment-list")

    def test_upload_crea_attachment_y_actualiza_attachments_url(self):
        """POST multipart → 201 + Ranch.attachments_url contiene la URL del archivo."""
        payload = {
            "model_name": "ranch",
            "object_id": str(self.ranch.pk),
            "file": _make_file("api_doc.pdf"),
        }
        res = self.client.post(self.list_url, payload, format="multipart")
        self.assertEqual(res.status_code, 201)
        self.assertIn("file_url", res.data)
        self.ranch.refresh_from_db()
        self.assertEqual(len(self.ranch.attachments_url), 1)

    def test_list_filtra_por_model_name_y_object_id(self):
        """GET con ?model_name=ranch&object_id=<pk> devuelve solo los de ese objeto."""
        # Crea adjunto para este rancho y otro rancho diferente
        Attachment.objects.create(content_object=self.ranch, file=_make_file("r1.pdf"))
        other = Ranch.objects.create(code="RCH-OTHER", name="Otro")
        Attachment.objects.create(content_object=other, file=_make_file("r2.pdf"))

        url = f"{self.list_url}?model_name=ranch&object_id={self.ranch.pk}"
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data["results"]), 1)

    def test_delete_elimina_attachment_y_actualiza_url(self):
        """DELETE → 204 + Ranch.attachments_url queda vacío."""
        att = Attachment.objects.create(
            content_object=self.ranch, file=_make_file("borrar.pdf")
        )
        detail_url = reverse("core:attachment-detail", args=[att.pk])
        res = self.client.delete(detail_url)
        self.assertEqual(res.status_code, 204)
        self.ranch.refresh_from_db()
        self.assertEqual(self.ranch.attachments_url, [])

    def test_upload_sin_autenticacion_retorna_401(self):
        """POST sin token → 401 Unauthorized."""
        anon_client = APIClient()
        payload = {
            "model_name": "ranch",
            "object_id": str(self.ranch.pk),
            "file": _make_file("anon.pdf"),
        }
        res = anon_client.post(self.list_url, payload, format="multipart")
        self.assertEqual(res.status_code, 401)
