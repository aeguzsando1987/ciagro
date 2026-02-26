from django.contrib import admin
from apps.geo_assets.models import Ranch, Plot, PlotVertex, RanchPartner

class PlotVertexInline(admin.TabularInline):
    model = PlotVertex
    extra = 0
    fields = ["level", "longitude", "latitude"]
    

@admin.register(Ranch)
class RanchAdmin(admin.ModelAdmin):
    list_display = ["id", "code", "name", "producer", "status", "country", "created_at"]
    list_filter = ["status", "country", "area_uom"]
    search_fields = ["code", "name", "producer__commercial_name"]
    ordering = ["name"]
    readonly_fields = ["id", "slug", "created_at", "updated_at", "created_by", "updated_by"]
    
    
@admin.register(Plot)
class PlotAdmin(admin.ModelAdmin):
    list_display = ["id", "code", "description", "ranch", "status", "total_area", "tech_spraying", "created_at"]
    list_filter = ["status", "ranch", "tech_spraying"]
    search_fields = ["code", "description", "ranch__code", "ranch__name"]
    ordering = ["code"]
    readonly_fields = ["id", "slug", "created_at", "updated_at", "created_by", "updated_by"]
    inlines = [PlotVertexInline]
    
    
@admin.register(RanchPartner)
class RanchPartnerAdmin(admin.ModelAdmin):
    list_display = ["id", "ranch", "partner", "relation_type"]
    list_filter = ["relation_type"]
    search_fields = ["ranch__code", "ranch__name", "partner__commercial_name"]
    
