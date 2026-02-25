import os
from decouple import config, UndefinedValueError

from django.db import transaction
from django.core.management.base import BaseCommand

from apps.users.models import Individual, User, UserRole

ROLE_NAME = "SuperAdmin"
ROLE_LEVEL = 5

class Command(BaseCommand):
    help = "Crear o actualizar usuario supoeradmin desde variables de entorno"
    
    def handle(self, *args, **options):
        username = config("CIAGRO_ADMIN_USERNAME", default="ciagro")
        email = config("CIAGRO_ADMIN_EMAIL", default="admin@ciagro.mx")
        password = config("CIAGRO_ADMIN_PASSWORD", default=None)
        
        if not password:
            self.stderr.write(self.style.ERROR("Falta la variable de entorno CIAGRO_ADMIN_PASSWORD"))
            return
        
        try:
            with transaction.atomic():
                role, role_created = UserRole.objects.get_or_create(
                    level=ROLE_LEVEL,
                    defaults={"role_name": ROLE_NAME}
                )
                if role_created:
                    self.stdout.write(self.style.SUCCESS(f"Rol {ROLE_NAME} creado"))
                    
                user, user_created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        "email": email,
                        "is_staff": True,
                        "is_superuser": True,
                        "user_role": role
                    },
                )
                
                if user_created:
                    user.set_password(password)
                    user.save()
                    self.stdout.write(self.style.SUCCESS(f"Usuario {username} creado"))
                else:
                    user.email = email
                    user.is_staff = True
                    user.is_superuser = True
                    user.user_role = role
                    user.set_password(password)
                    user.save()
                    self.stdout.write(self.style.SUCCESS(f"Usuario {username} actualizado"))
                    
                individual, individual_created = Individual.objects.get_or_create(
                    user=user,
                    defaults={
                        "first_name":"CIAgro", 
                        "last_name":"Alpha", 
                        "phone":""
                        }
                    )
                
                if individual_created:
                    self.stdout.write(self.style.SUCCESS(f"Individuo de {username} creado"))

                
        except Exception as ex:
            self.stderr.write(self.style.ERROR(ex))
            return
        
        self.stdout.write(self.style.SUCCESS(
            f"Comando finalizado: Admin\nusuario:{username}\ncorreo:{email}\nusuario inicial creado/actualizado exitosamente"
            ))
