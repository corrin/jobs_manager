"""
Modern Timesheet Serializers

DRF serializers for modern timesheet API endpoints using CostSet/CostLine system
"""

from rest_framework import serializers

from apps.job.models import Job


class ModernTimesheetJobSerializer(serializers.ModelSerializer):
    """Serializer for jobs in timesheet context using modern CostSet system"""

    client_name = serializers.CharField(source="client.name", read_only=True)
    has_actual_costset = serializers.SerializerMethodField()

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
        ]

    def get_has_actual_costset(self, obj):
        """Check if job has an actual cost set"""
        return obj.get_latest("actual") is not None


class ModernStaffSerializer(serializers.Serializer):
    """Serializer for staff in timesheet context"""

    id = serializers.CharField()
    name = serializers.CharField()
    firstName = serializers.CharField()
    lastName = serializers.CharField()
    email = serializers.CharField()
    avatarUrl = serializers.CharField(allow_null=True)


class WeeklyTimesheetDataSerializer(serializers.Serializer):
    """Serializer for comprehensive weekly timesheet data"""

    start_date = serializers.DateField()
    end_date = serializers.DateField()
    week_days = serializers.ListField(child=serializers.DateField())
    staff_data = serializers.ListField()  # Complex nested data
    weekly_summary = serializers.DictField()
    job_metrics = serializers.DictField()
    summary_stats = serializers.DictField()
    export_mode = serializers.CharField()
    is_current_week = serializers.BooleanField()
    navigation = serializers.DictField(required=False)


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
