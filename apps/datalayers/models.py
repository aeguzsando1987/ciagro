from django.db import models

class DataLayer(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=100, unique=True)
    definition_scheme = models.JSONField(
        default=dict,
        help_text="Contrato de ingesta: campos obligatorios, tipos y alias para parseo de datos deCSV/sensores."
    )
    evaluation_scheme = models.JSONField(
        default=dict,
        help_text="Contrato de  agronomica: ejes kiviat, rangos de colorimetria y preguntas manuales."
    )
    attachments_url = models.JSONField(default=list, blank=True)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    class Meta:
        db_table = "datalayers"
        ordering = ["name"]
        
