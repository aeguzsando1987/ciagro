from django.contrib import admin
from apps.core.admin import AttachmentInline, SoftDeleteAdminMixin
from apps.core.models import Attachment
from apps.geo_assets.models import Ranch, Plot, PlotVertex, RanchPartner
from apps.geo_assets.widgets import LeafletPolygonWidget
from apps.core.widgets import AdditionalParamsWidget

class PlotVertexInline(admin.TabularInline):
    model = PlotVertex
    extra = 0
    fields = ["level", "longitude", "latitude"]
    

@admin.register(Ranch)
class RanchAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = ["id", "code", "name", "producer", "status", "country", "created_at"]
    list_filter = ["status", "country", "area_uom"]
    search_fields = ["code", "name", "producer__commercial_name"]
    ordering = ["name"]
    readonly_fields = ["id", "slug", "created_at", "updated_at", "created_by", "updated_by",
                       "is_deleted", "deleted_at", "deleted_by"]
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

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "additional_params":
            kwargs["widget"] = AdditionalParamsWidget()
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    class Media:
        js = ["geography/admin_country_state.js"]


@admin.register(Plot)
class PlotAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = ["id", "code", "description", "ranch", "status", "total_area", "tech_spraying", "created_at"]
    list_filter = ["status", "ranch", "tech_spraying"]
    search_fields = ["code", "description", "ranch__code", "ranch__name"]
    ordering = ["code"]
    # centroid y total_area son auto-calculados en Plot.save() desde geom — solo lectura.
    readonly_fields = [
        "id", "slug", "centroid", "total_area",
        "created_at", "updated_at", "created_by", "updated_by",
        "is_deleted", "deleted_at", "deleted_by",
    ]
    fieldsets = [
        ("Mapa de parcela", {
            # Primera pestaña: el mapa Leaflet ocupa el protagonismo.
            # centroid y total_area se auto-calculan al guardar.
            "fields": ["geom", "centroid", "total_area"],
        }),
        ("Información general", {
            "fields": ["code", "description", "ranch", "status", "tech_spraying", "comments"],
        }),
        ("Datos adicionales", {
            "fields": ["additional_params", "attachments_url"],
        }),
        ("Auditoría", {
            "fields": ["id", "slug", "created_at", "updated_at", "created_by", "updated_by",
                       "is_deleted", "deleted_at", "deleted_by"],
            "classes": ["collapse"],
        }),
    ]
    inlines = [PlotVertexInline, AttachmentInline]

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        """Aplica el widget Leaflet al campo geom y el K-V widget a additional_params."""
        if db_field.name == "geom":
            kwargs["widget"] = LeafletPolygonWidget()
        elif db_field.name == "additional_params":
            kwargs["widget"] = AdditionalParamsWidget()
        return super().formfield_for_dbfield(db_field, request, **kwargs)

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
    
    
@admin.register(RanchPartner)
class RanchPartnerAdmin(admin.ModelAdmin):
    list_display = ["id", "ranch", "partner", "relation_type"]
    list_filter = ["relation_type"]
    search_fields = ["ranch__code", "ranch__name", "partner__commercial_name"]
    
