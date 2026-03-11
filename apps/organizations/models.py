from django.db import models
from django.utils.text import slugify

from apps.core.models import BaseAuditModel

class AgroSector(models.Model): # Agro sector
    id = models.AutoField(primary_key=True)
    sector_name = models.CharField(max_length=100, unique=True)
    scian_code = models.CharField(max_length=20, blank=True)
    activity_name = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.sector_name
    
    class Meta:
        db_table = "agro_sectors"
        ordering = ["sector_name"]
        
class AgroUnit(BaseAuditModel): # Entidad agronomica 
    
    class UnitType(models.TextChoices):
        PRODUCTOR="Productor", "Productor"
        ACOPIADORA="Acopiadora de grano", "Acopiadora de grano"
        ASOCIACION="Asociación agrícola", "Asociación agrícola"
        EMPAQUE="Empaque", "Empaque"
        LABORATORIO="Laboratorio", "Laboratorio"
        CONSULTORIA="Consultoria", "Consultoria"
        OTRO="Otro", "Otro"
        
    class Status(models.TextChoices):
        ACTIVE = "active", "Activo"
        INACTIVE = "inactive", "Inactivo"
        SUSPENDED = "suspended", "Suspendido"
        PENDING = "pending", "Pendiente"
        
    class TaxType(models.TextChoices):
        RFC ="RFC", "RFC"
        TAXID ="Tax ID", "Tax ID"
        CUIT = "CUIT", "CUIT"
        RIF = "RIF", "RIF"
        TIN = "TIN", "TIN"
        SSN = "SSN", "SSN"
        NIF = "NIF", "NIF"
        CIF = "CIF", "CIF"
        RUT = "RUT", "RUT"
        OTRO = "Otro", "Otro"
        
    unit_type = models.CharField(max_length=25, choices=UnitType.choices, default=UnitType.PRODUCTOR)
    agro_sector = models.ForeignKey(AgroSector, null=True, blank=True, on_delete=models.SET_NULL, related_name="agro_units")
    
    code = models.CharField(max_length=20, unique=True)
    tax_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    tax_type = models.CharField(max_length=25, choices=TaxType.choices, null=True, blank=True)
    company_name = models.CharField(max_length=200, blank=True)
    commercial_name = models.CharField(max_length=200)
    headcount = models.PositiveSmallIntegerField(null=True, blank=True)
    
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    
    address_line_1 = models.CharField(max_length=255, blank=True)
    address_line_2 = models.CharField(max_length=255, blank=True)
    location_url = models.URLField(max_length=500, blank=True)
    country = models.ForeignKey("geography.Country", null=True, blank=True, on_delete=models.SET_NULL, related_name="agro_units")
    state = models.ForeignKey("geography.State", null=True, blank=True, on_delete=models.SET_NULL, related_name="agro_units")
    default_contact = models.ForeignKey(
        "organizations.Contact",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="primary_for_units"
    )

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    additional_params = models.JSONField(default=dict, blank=True)
    attachments_url = models.JSONField(default=list, blank=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    
    def __str__(self):
        return f"{self.code} - {self.commercial_name}"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.commercial_name)
            slug, counter = base_slug, 1
            while AgroUnit.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)
        
    class Meta:
        db_table = "agro_units"
        ordering = ["commercial_name"]
    

class Contact(BaseAuditModel):
    name  = models.CharField(max_length=200)
    address_line_1 = models.CharField(max_length=255, blank=True)
    address_line_2 = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)

    def __str__(self):
        return f"{self.name} | Email: {self.email} - Tel: {self.phone}"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug, counter = base_slug, 1
            while Contact.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)
        
    class Meta:
        db_table = "contacts"
        ordering = ["name"]
        

class ContactAssignment(models.Model):
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name="assignments")
    agro_unit = models.ForeignKey(AgroUnit, on_delete=models.CASCADE, related_name="contact_assignments")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.contact.name} - {self.agro_unit.commercial_name}"

    class Meta:
        db_table = "contact_assignments"
        unique_together = [["contact", "agro_unit"]]
    
