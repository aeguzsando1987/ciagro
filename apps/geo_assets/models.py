from django.db import models
from django.utils.text import slugify


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
    lat = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True) # No usaremos geom?
    lon = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True) # No usaremos geom?
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