from django.contrib import admin
from apps.core.admin import SoftDeleteAdminMixin
from apps.organizations.models import AgroSector, AgroUnit, Contact, ContactAssignment
from apps.users.models import UserAssignment


class ContactAssignmentInline(admin.TabularInline):
    """
    Muestra los contactos asignados a esta AgroUnit directamente en su formulario.
    raw_id_fields evita un <select> gigante cuando hay muchos contactos.
    """
    model = ContactAssignment
    extra = 1
    raw_id_fields = ["contact"]
    fields = ["contact", "contact_name", "contact_email", "contact_phone"]
    readonly_fields = ["contact_name", "contact_email", "contact_phone"]
    verbose_name = "Contacto asignado"
    verbose_name_plural = "Contactos asignados a esta unidad"

    @admin.display(description="Nombre")
    def contact_name(self, obj):
        return f"{obj.contact.name}" or "—"

    @admin.display(description="Email")
    def contact_email(self, obj):
        return obj.contact.email or "—"

    @admin.display(description="Teléfono")
    def contact_phone(self, obj):
        return obj.contact.phone or "—"


class UserAssignmentInline(admin.TabularInline):
    """
    Muestra los usuarios asignados a esta AgroUnit directamente en su formulario.
    raw_id_fields evita un <select> gigante cuando hay muchos usuarios.
    """
    model = UserAssignment
    extra = 1
    raw_id_fields = ["user"]
    fields = ["user", "individual_name", "created_at"]
    readonly_fields = ["individual_name", "created_at"]
    verbose_name = "Usuario asignado"
    verbose_name_plural = "Usuarios asignados a esta unidad"

    @admin.display(description="Nombre")
    def individual_name(self, obj):
        """Muestra first_name + last_name del Individual vinculado al User."""
        try:
            ind = obj.user.individual
            return f"{ind.first_name} {ind.last_name}"
        except Exception:
            return "—"


@admin.register(AgroSector)
class AgroSectorAdmin(admin.ModelAdmin):
    list_display = ["id", "sector_name", "scian_code", "activity_name"]
    search_fields = ["sector_name", "scian_code"]
    ordering = ["sector_name"]


@admin.register(AgroUnit)
class AgroUnitAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = ["id", "commercial_name", "unit_type", "status", "country", "created_at"]
    list_filter = ["unit_type", "status", "country"]
    search_fields = ["code", "commercial_name", "company_name", "tax_id"]
    ordering = ["commercial_name"]
    readonly_fields = ["id", "slug", "created_at", "updated_at", "created_by", "updated_by",
                       "is_deleted", "deleted_at", "deleted_by"]
    inlines = [UserAssignmentInline, ContactAssignmentInline]

    class Media:
        js = ["geography/admin_country_state.js"]
    
@admin.register(Contact)
class ContactAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = ["id", "name", "email", "phone", "created_at"]
    search_fields = ["name", "email", "phone"]
    ordering = ["name"]
    readonly_fields = ["id", "slug", "created_at", "updated_at", "created_by", "updated_by",
                       "is_deleted", "deleted_at", "deleted_by"]
    
    
@admin.register(ContactAssignment)
class ContactAssignmentAdmin(admin.ModelAdmin):
    list_display = ["id", "contact", "agro_unit", "created_at"]
    ordering = ["agro_unit"]
    search_fields = ["contact__name", "agro_unit__commercial_name"]