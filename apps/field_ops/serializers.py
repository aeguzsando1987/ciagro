from rest_framework import serializers
from apps.field_ops.models import CropCatalog, PestCatalog, FieldTask, FieldTaskReport, TaskReportIssue
from apps.datalayers.models import DataLayer

class CropCatalogSerializer(serializers.ModelSerializer):
    class Meta:
        model = CropCatalog
        fields = ["id", "name", "description", "photo_url", 
                "additional_params", "attachments_url"]
        read_only_fields = ["id"]
        

class PestCatalogSerializer(serializers.ModelSerializer):
    default_crop = CropCatalogSerializer(read_only=True)
    default_crop_id = serializers.PrimaryKeyRelatedField(
        queryset=CropCatalog.objects.all(), 
        source="default_crop", 
        write_only=True, 
        required=False, 
        allow_null=True
    )
    
    class Meta:
        model = PestCatalog
        fields = ["id", "name", "default_crop", "default_crop_id", 
                "description", "photo_url", "ref_value",
                "additional_params", "attachments_url",]
        read_only_fields = ["id"]
        
        
class TaskReportIssueSerializer(serializers.ModelSerializer):
    severity_alert_display = serializers.CharField(source="get_severity_alert_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = TaskReportIssue
        fields = [
            "id", "report",
            "issue_title", "description", "agro_activity", "issue_type",
            "probability", "severity_alert", "severity_alert_display",
            "expected_solution", "reached_solution",
            "status", "status_display", "is_ruled",
            "identification_date", "solution_date", "notes",
        ]
        read_only_fields = ["id", "severity_alert_display", "status_display"]


class FieldTaskReportSerializer(serializers.ModelSerializer):
    issues = TaskReportIssueSerializer(many=True, read_only=True)

    class Meta:
        model = FieldTaskReport
        fields = [
            "id", "task", "plot", "evaluator",
            "summary_data", "report_date",
            "evaluation_data", "scan_date", "report_score",
            "main_causes", "summary_1", "summary_2", "conclusion",
            "internal_comments", "map_url", "attachments_url",
            "is_valid", "validation_token",
            "issues",
        ]
        read_only_fields = ["id", "summary_data", "report_date", "issues"]


class FieldTaskSerializer(serializers.ModelSerializer):
    crop = CropCatalogSerializer(read_only=True)
    datalayer_code = serializers.CharField(source="datalayer.code", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    
    crop_id = serializers.PrimaryKeyRelatedField(
        queryset=CropCatalog.objects.all(), 
        source="crop", 
        write_only=True, 
        required=False, 
        allow_null=True
    )
    datalayer_id = serializers.PrimaryKeyRelatedField(
        queryset=DataLayer.objects.all(),
        source="datalayer",
        write_only=True,
        required=False,
        allow_null=True
    )
    class Meta:
        model = FieldTask
        fields = ["id", "voucher_code",
                "title", "cycle",
                "status", "status_display",
                "crop", "crop_id",
                "datalayer_code", "datalayer_id",
                "individual", "agro_unit",
                "plot", "parent_task",
                "est_start_date", "est_finish_date",
                "actual_start_date", "actual_finish_date",
                "location_url", "attachments_url",]
        read_only_fields = ["id", "status_display", "datalayer_code"]
        


