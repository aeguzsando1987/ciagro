from django.contrib import admin
from apps.datalayers.models import DataLayer


@admin.register(DataLayer)
class DatalayerAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "created_at"]
    search_fields = ["code", "name"]
    ordering = ["created_at"]
    readonly_fields = ["created_at"]
    

