from django.db import models

class Country(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    iso_2 = models.CharField(max_length=2, unique=True)
    iso_3 = models.CharField(max_length=3, unique=True)
    
    class Meta:
        db_table = 'countries'
        ordering = ['name']
        
    def __str__(self):
        return f"{self.name}-({self.iso_2})-({self.iso_3})" 
    
    
class State(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10)
    country = models.ForeignKey(Country, 
                                on_delete=models.CASCADE,
                                related_name='states')
    
    class Meta:
        db_table = 'states'
        ordering = ['name']
        unique_together = ['country', 'code']
        
    def __str__(self):
        return f"{self.name}-({self.code})-({self.country.iso_3})"