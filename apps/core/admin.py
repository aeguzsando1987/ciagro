from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline
from django.utils import timezone
from apps.core.models import Attachment


class SoftDeleteAdminMixin:
    """
    Mixin para admins de modelos que heredan BaseAuditModel.

    Intercepta las dos rutas de borrado del admin Django:
      - delete_model: botón "Eliminar" en el change form (un objeto)
      - delete_queryset: acción "Delete selected" en el listado (varios objetos)

    En lugar de hacer DELETE real, marca is_deleted=True + deleted_at + deleted_by.

    get_queryset filtra los registros borrados del listado (is_deleted=False),
    pero los datos permanecen en la BD para auditoría.
    """

    def delete_model(self, request, obj):
        """Borrado individual desde el change form."""
        obj.is_deleted = True
        obj.deleted_at = timezone.now()
        obj.deleted_by = request.user
        obj.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])

    def delete_queryset(self, request, queryset):
        """Borrado masivo desde el listado (acción 'Delete selected')."""
        queryset.update(
            is_deleted=True,
            deleted_at=timezone.now(),
            deleted_by=request.user,
        )

    def get_queryset(self, request):
        """Excluir registros marcados como borrados del listado admin."""
        return super().get_queryset(request).filter(is_deleted=False)

    def save_model(self, request, obj, form, change):
        """
        Asigna created_by (solo al crear) y updated_by en cada guardado.
        Los campos existen en BaseAuditModel pero el admin no los llena
        por defecto: request.user solo está disponible en la capa de vista.
        """
        if not change:          # creación
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


class AttachmentInline(GenericTabularInline):
    """
    Inline reutilizable para adjuntar archivos a cualquier modelo del proyecto.

    Uso en un ModelAdmin:
        from apps.core.admin import AttachmentInline
        from apps.core.models import Attachment

        class MyModelAdmin(admin.ModelAdmin):
            inlines = [AttachmentInline]

            def save_formset(self, request, form, formset, change):
                if formset.model is Attachment:
                    instances = formset.save(commit=False)
                    for inst in instances:
                        if not inst.pk:
                            inst.uploaded_by = request.user
                        inst.save()
                    formset.save_m2m()
                else:
                    super().save_formset(request, form, formset, change)

    Al guardar, Attachment._sync_parent_urls() actualiza automáticamente
    el campo attachments_url del objeto padre con las URLs activas.
    """

    model = Attachment
    extra = 1
    fields = ["file", "filename", "uploaded_by", "uploaded_at"]
    readonly_fields = ["uploaded_by", "uploaded_at"]
    verbose_name = "Archivo adjunto"
    verbose_name_plural = "Archivos adjuntos"
