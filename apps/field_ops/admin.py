from django.contrib import admin
from apps.field_ops.models import CropCatalog, PestCatalog, FieldTask, FieldTaskReport, TaskReportIssue


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


class TaskReportIssueInline(admin.TabularInline):
    model = TaskReportIssue
    extra = 0
    fields = ['issue_title', 'severity_alert', 'status', 'is_ruled', 'identification_date']
    show_change_link = True


@admin.register(FieldTaskReport)
class FieldTaskReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'task', 'plot', 'report_date', 'report_score', 'is_valid']
    list_filter = ['is_valid', 'report_date']
    search_fields = ['task__voucher_code']
    ordering = ['-report_date']
    readonly_fields = ['id', 'summary_data', 'report_date']
    inlines = [TaskReportIssueInline]


@admin.register(TaskReportIssue)
class TaskReportIssueAdmin(admin.ModelAdmin):
    list_display = ['issue_title', 'severity_alert', 'status', 'is_ruled', 'report']
    list_filter = ['severity_alert', 'status', 'is_ruled']
    search_fields = ['issue_title', 'report__task__voucher_code']
    readonly_fields = ['id']
