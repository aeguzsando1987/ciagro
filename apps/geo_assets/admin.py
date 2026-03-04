from django.contrib import admin
from apps.core.admin import SoftDeleteAdminMixin
from apps.geo_assets.models import Ranch, Plot, PlotVertex, RanchPartner

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

    class Media:
        js = ["geography/admin_country_state.js"]


@admin.register(Plot)
class PlotAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = ["id", "code", "description", "ranch", "status", "total_area", "tech_spraying", "created_at"]
    list_filter = ["status", "ranch", "tech_spraying"]
    search_fields = ["code", "description", "ranch__code", "ranch__name"]
    ordering = ["code"]
    readonly_fields = ["id", "slug", "created_at", "updated_at", "created_by", "updated_by",
                       "is_deleted", "deleted_at", "deleted_by"]
    inlines = [PlotVertexInline]
    
    
@admin.register(RanchPartner)
class RanchPartnerAdmin(admin.ModelAdmin):
    list_display = ["id", "ranch", "partner", "relation_type"]
    list_filter = ["relation_type"]
    search_fields = ["ranch__code", "ranch__name", "partner__commercial_name"]
    
