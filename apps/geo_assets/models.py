from django.utils.text import slugify
from django.contrib.gis.db import models

from apps.core.models import BaseAuditModel

class Ranch(BaseAuditModel):
    
    class Status(models.TextChoices):
        ACTIVE = "active", "Activo"
        INACTIVE = "inactive", "Inactivo"
        CLOSED = "closed", "Cerrado"
        
    class AreaUoM(models.TextChoices):
        HA = "ha", "Hectareas"
        AC = "ac", "Acres"
        M2 = "m2", "Metros cuadrados"
        
    code = models.CharField(max_length=20, unique=True)
    producer = models.ForeignKey("organizations.AgroUnit", 
                                null=True, 
                                blank=True, 
                                on_delete=models.SET_NULL, 
                                related_name="ranches")
    name = models.CharField(max_length=200)
    address_line_1 = models.CharField(max_length=255, blank=True)
    address_line_2 = models.CharField(max_length=255, blank=True)
    location_url = models.URLField(max_length=500, blank=True)
    lat = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    lon = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    geom = models.PointField(srid=4326, null=True, blank=True)
    country = models.ForeignKey("geography.Country", 
                                null=True, 
                                blank=True, 
                                on_delete=models.SET_NULL, 
                                related_name="ranches")
    state = models.ForeignKey("geography.State", 
                                null=True, 
                                blank=True, 
                                on_delete=models.SET_NULL, 
                                related_name="ranches")
    city = models.CharField(max_length=100, null=True, blank=True)
    area_uom = models.CharField(max_length=10, choices=AreaUoM.choices, default=AreaUoM.M2)
    total_area = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    attachments_url = models.JSONField(default=list, blank=True)
    additional_params = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug, counter = base_slug, 1
            while Ranch.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    class Meta:
        db_table = "ranches"
        ordering = ["name"]
        
        
class Plot(BaseAuditModel):
    
    class Status(models.TextChoices):
        ACTIVE = "active", "Activo"
        INACTIVE = "inactive", "Inactivo"
        DEPRECATED = "deprecated", "Depreciado"
        
    code = models.CharField(max_length=30, unique=True)
    description = models.CharField(max_length=500, blank=True)
    ranch = models.ForeignKey("geo_assets.Ranch", on_delete=models.CASCADE, related_name="plots")
    geom = models.PolygonField(srid=4326, null=True, blank=True)
    centroid = models.PointField(srid=4326, null=True, blank=True)
    total_area = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tech_spraying = models.BooleanField(default=False)
    comments = models.TextField(null=True, blank=True)
    additional_params = models.JSONField(default=dict, blank=True)
    attachments_url = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.code)
            slug, counter = base_slug, 1
            while Plot.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.code} - {self.description}"
    
    class Meta:
        db_table = "plots"
        ordering = ["code"]
        
        
class PlotVertex(models.Model):
    """
    Esta entidad es completamente auxiliar para poder guardar las coordenadas de los vertices de parcelas.
    Se pensó originalmente para almacenar lo puntos, coenctarlos y crear el poligono manualemnte, para despues 
    poder usar las librerias de mapas para dibujarlos y renderizarlos en el frontend.
    """
    plot = models.ForeignKey("geo_assets.Plot", on_delete=models.CASCADE, related_name="vertices")
    level = models.IntegerField()
    longitude = models.FloatField()
    latitude = models.FloatField()
    
    class Meta:
        db_table = "plot_vertexes"
        ordering = ["plot", "level"]
        unique_together = [["plot", "level"]]
        

class RanchPartner(models.Model):
    """
    Entidad pensada para relacionar Ranchos con laboratorios, acopiadoras de grano y asociaciones.
    Mas adelante se puede extender para otros tipos de relaciones segun vaya creciendo la definición
    de agrounidades.
    """
    class RelationType(models.TextChoices):
        GUILD = "guild", "Asociación Agrícola"
        GRAIN_COLLECTOR = "grain_collector", "Acopiadora de Grano"
        LAB = "lab", "Laboratorio"
    
    ranch = models.ForeignKey("geo_assets.Ranch", on_delete=models.CASCADE, related_name="partners")
    partner = models.ForeignKey("organizations.AgroUnit", on_delete=models.CASCADE, related_name="ranch_relations")
    relation_type = models.CharField(max_length=20, choices=RelationType.choices)
    
    class Meta:
        db_table = "ranch_partners"
        unique_together = [["ranch", "partner", "relation_type"]]
        
    