from django.contrib import admin
from apps.field_ops.models import CropCatalog, PestCatalog, FieldTask

@admin.register(CropCatalog)
class CropCatalogAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'description']
    search_fields = ['name']
    ordering = ['name']

@admin.register(PestCatalog)
class PestCatalogAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'default_crop', 'ref_value']
    list_filter = ['default_crop']
    search_fields = ['name', 'default_crop__name']
    ordering = ['name']
    

@admin.register(FieldTask)
class FieldTaskAdmin(admin.ModelAdmin):
    list_display = ['voucher_code', 'title', 'status', 'cycle', 'agro_unit', 'individual', 'est_start_date', 'est_finish_date']
    list_filter = ['status', 'cycle', 'agro_unit', 'individual']
    search_fields = ['voucher_code', 'title']
    ordering = ['-est_start_date']
    readonly_fields = ['id']
    


    


