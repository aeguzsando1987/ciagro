from django.contrib import admin
from apps.organizations.models import AgroSector, AgroUnit

@admin.register(AgroSector)
class AgroSectorAdmin(admin.ModelAdmin):
    list_display = ["id", "sector_name", "scian_code", "activity_name"]
    search_fields = ["sector_name", "scian_code"]
    ordering = ["sector_name"]
    

@admin.register(AgroUnit)
class AgroUnitAdmin(admin.ModelAdmin):
    list_display = ["id", "commercial_name", "unit_type", "status", "country", "created_at"]
    list_filter = ["unit_type", "status", "country"]
    search_fields = ["code", "commercial_name", "company_name", "tax_id"]
    ordering = ["commercial_name"]
    readonly_fields = ["id", "slug", "created_at", "updated_at", "created_by", "updated_by"]
    


# Register your models here.
