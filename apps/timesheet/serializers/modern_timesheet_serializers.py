"""
Modern Timesheet Serializers

DRF serializers for modern timesheet API endpoints using CostSet/CostLine system
"""

from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from apps.job.models import Job
from apps.timesheet.serializers.daily_timesheet_serializers import (
    SummaryStatsSerializer,
)


class ModernTimesheetJobSerializer(serializers.ModelSerializer):
    """Serializer for jobs in timesheet context using modern CostSet system"""

    client_name = serializers.CharField(
        source="client.name", read_only=True, required=False, allow_null=True
    )
    has_actual_costset = serializers.SerializerMethodField()
    leave_type = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = [
            "id",
            "job_number",
            "name",
            "client_name",
            "status",
            "charge_out_rate",
            "has_actual_costset",
            "leave_type",
        ]

    def get_has_actual_costset(self, obj) -> bool:
        """Check if job has an actual cost set"""
        return obj.get_latest("actual") is not None

    def get_leave_type(self, obj) -> str:
        """Get leave type if this is a payroll job"""
        return obj.get_leave_type()


class ModernStaffSerializer(serializers.Serializer):
    """Serializer for staff in timesheet context"""

    id = serializers.CharField()
    name = serializers.CharField()
    firstName = serializers.CharField()
    lastName = serializers.CharField()
    email = serializers.CharField()
    avatarUrl = serializers.CharField(allow_null=True)
    wageRate = serializers.DecimalField(max_digits=10, decimal_places=2)


class WeeklySummarySerializer(serializers.Serializer):
    """Serializer for weekly summary data"""

    total_hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    staff_count = serializers.IntegerField()
    billable_percentage = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )


class JobMetricsSerializer(serializers.Serializer):
    """Serializer for job metrics in weekly timesheet context"""

    total_estimated_profit = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_actual_profit = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_profit = serializers.DecimalField(max_digits=10, decimal_places=2)


class WeeklyStaffDataWeeklyHoursSerializer(serializers.Serializer):
    """Serializer for weekly hours data of staff with payroll fields"""

    day = serializers.CharField()
    hours = serializers.DecimalField(max_digits=5, decimal_places=2)
    billable_hours = serializers.DecimalField(max_digits=5, decimal_places=2)
    scheduled_hours = serializers.DecimalField(max_digits=5, decimal_places=2)
    status = serializers.CharField()
    leave_type = serializers.CharField(
        allow_blank=True, required=False, allow_null=True
    )
    has_leave = serializers.BooleanField(default=False)

    # Xero Payroll posting categories (only hours that will be posted to Xero)
    billed_hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    unbilled_hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    overtime_1_5x_hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    overtime_2x_hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    sick_leave_hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    annual_leave_hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    other_leave_hours = serializers.DecimalField(max_digits=10, decimal_places=2)


class WeeklyStaffDataSerializer(serializers.Serializer):
    """Serializer for staff data in weekly timesheet context with payroll fields"""

    staff_id = serializers.UUIDField()
    name = serializers.CharField()
    weekly_hours = WeeklyStaffDataWeeklyHoursSerializer(many=True)

    total_hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_billable_hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_scheduled_hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    billable_percentage = serializers.DecimalField(max_digits=5, decimal_places=2)
    status = serializers.CharField()

    # Xero Payroll posting categories (weekly totals, excludes unpaid hours)
    total_billed_hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_unbilled_hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_overtime_1_5x_hours = serializers.DecimalField(
        max_digits=10, decimal_places=2
    )
    total_overtime_2x_hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_sick_leave_hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_annual_leave_hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_other_leave_hours = serializers.DecimalField(max_digits=10, decimal_places=2)


@extend_schema_serializer(component_name="WeeklyTimesheetData")
class WeeklyTimesheetDataSerializer(serializers.Serializer):
    """Serializer for complete weekly timesheet data with payroll fields"""

    start_date = serializers.CharField()
    end_date = serializers.CharField()
    week_days = serializers.ListField(child=serializers.CharField())
    staff_data = WeeklyStaffDataSerializer(many=True)
    weekly_summary = WeeklySummarySerializer()
    job_metrics = JobMetricsSerializer()
    summary_stats = SummaryStatsSerializer()
    export_mode = serializers.CharField()
    is_current_week = serializers.BooleanField()

    # Optional fields added by views
    navigation = serializers.DictField(required=False, allow_null=True)
    weekend_enabled = serializers.BooleanField(required=False)
    week_type = serializers.CharField(required=False, allow_blank=True)


class PaidAbsenceRequestSerializer(serializers.Serializer):
    """Serializer for paid absence request submission"""

    staff_id = serializers.UUIDField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    leave_type = serializers.ChoiceField(
        choices=[
            ("annual", "Annual Leave"),
            ("sick", "Sick Leave"),
            ("other", "Other Leave"),
        ]
    )
    hours_per_day = serializers.FloatField(min_value=0.1, max_value=24.0)
    description = serializers.CharField(
        required=False, allow_blank=True, max_length=500
    )

    def validate(self, data):
        """Validate that end date is not before start date"""
        if data["end_date"] < data["start_date"]:
            raise serializers.ValidationError("End date cannot be before start date")
        return data


class StaffListResponseSerializer(serializers.Serializer):
    """Serializer for staff list API response"""

    staff = ModernStaffSerializer(many=True)
    total_count = serializers.IntegerField()


class JobsListResponseSerializer(serializers.Serializer):
    """Serializer for jobs list API response"""

    jobs = ModernTimesheetJobSerializer(many=True)
    total_count = serializers.IntegerField()
