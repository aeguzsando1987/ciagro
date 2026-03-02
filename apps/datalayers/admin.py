from django.contrib import admin
from apps.datalayers.models import DataLayer
from apps.datalayers.widgets import DefinitionSchemeWidget, EvaluationSchemeWidget


@admin.register(DataLayer)
class DatalayerAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "created_at"]
    search_fields = ["code", "name"]
    ordering = ["created_at"]
    readonly_fields = ["created_at"]

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        """
        Aplica widget personalizado según el nombre del campo JSONB.
        formfield_for_dbfield (no formfield_overrides) porque necesitamos
        un widget DISTINTO para cada campo JSONField.
        """
        if db_field.name == "definition_scheme":
            kwargs["widget"] = DefinitionSchemeWidget()
        elif db_field.name == "evaluation_scheme":
            kwargs["widget"] = EvaluationSchemeWidget()
        return super().formfield_for_dbfield(db_field, request, **kwargs)
    

