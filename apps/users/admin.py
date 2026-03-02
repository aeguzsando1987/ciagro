from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.users.models import UserRole, User, WorkRole, Individual, UserAssignment

@admin.register(UserRole) # Decorador para registrar el modelo
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ["role_name", "level"]
    ordering = ["level"]
    
@admin.register(WorkRole)
class WorkRoleAdmin(admin.ModelAdmin):
    list_display = ["work_name", "activity_description"]
    ordering = ["work_name"]
    
class IndividualInline(admin.TabularInline):
    model = Individual
    fk_name = "user"
    extra = 0
    fields = ["first_name", "last_name", "phone", "work_role"]
    
@admin.register(UserAssignment)
class UserAssignmentAdmin(admin.ModelAdmin):
    list_display = ["user", "agro_unit", "created_at"]
    list_filter = ["agro_unit"]
    search_fields = ["user__username", "user__email",
                     "agro_unit__code", "agro_unit__commercial_name"]
    ordering = ["agro_unit"]


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = [IndividualInline]
    list_display = ["username", "email", "status", "user_role", "is_active"]
    list_filter = ["status", "user_role"]
    fieldsets = BaseUserAdmin.fieldsets + (
        ("CIAgro", {"fields": ("status", "user_role", "requires_password_change")}),
    )

