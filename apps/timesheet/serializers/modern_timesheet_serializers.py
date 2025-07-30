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

    def get_has_actual_costset(self, obj) -> bool:
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
    wageRate = serializers.DecimalField(max_digits=10, decimal_places=2)


class WeeklyStaffDataWeeklyHoursSerializer(serializers.Serializer):
    """Serializer for weekly hours data of staff"""

    date = serializers.DateField()
    hours = serializers.DecimalField(max_digits=5, decimal_places=2)


class WeeklyStaffDataSerializer(serializers.Serializer):
    """Serializer for staff data in weekly timesheet context"""

    id = serializers.UUIDField()
    name = serializers.CharField()
    weekly_hours = WeeklyStaffDataWeeklyHoursSerializer(many=True)


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


class WeeklyTimesheetDataSerializer(serializers.Serializer):
    """Serializer for comprehensive weekly timesheet data"""

    start_date = serializers.DateField()
    end_date = serializers.DateField()
    week_days = serializers.ListField(child=serializers.DateField())
    week_start = serializers.CharField()
    staff_data = WeeklyStaffDataSerializer(many=True)
    weekly_summary = WeeklySummarySerializer()
    job_metrics = JobMetricsSerializer()
    summary_stats = serializers.DictField()
    export_mode = serializers.CharField()
    is_current_week = serializers.BooleanField()
    navigation = serializers.DictField(required=False)


class IMSWeeklyStaffDataWeeklyHoursSerializer(serializers.Serializer):
    """Serializer for weekly hours data of staff in IMS context"""

    day = serializers.CharField()
    hours = serializers.DecimalField(max_digits=5, decimal_places=2)
    billable_hours = serializers.DecimalField(max_digits=5, decimal_places=2)
    scheduled_hours = serializers.DecimalField(max_digits=5, decimal_places=2)
    status = serializers.CharField()
    leave_type = serializers.CharField(allow_blank=True, required=False)
    has_leave = serializers.BooleanField(default=False)

    # IMS-specific fields
    standard_hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    time_and_half_hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    double_time_hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    unpaid_hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    overtime = serializers.DecimalField(max_digits=10, decimal_places=2)
    leave_hours = serializers.DecimalField(max_digits=10, decimal_places=2)


class IMSWeeklyStaffDataSerializer(serializers.Serializer):
    """Serializer for staff data in IMS weekly timesheet context"""

    staff_id = serializers.UUIDField()
    name = serializers.CharField()
    weekly_hours = IMSWeeklyStaffDataWeeklyHoursSerializer(many=True)

    total_hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_billable_hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    billable_percentage = serializers.DecimalField(max_digits=5, decimal_places=2)
    status = serializers.CharField()

    # IMS-specific fields
    total_standard_hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_time_and_half_hours = serializers.DecimalField(
        max_digits=10, decimal_places=2
    )
    total_double_time_hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_overtime = serializers.DecimalField(max_digits=10, decimal_places=2)


class IMSWeeklyTimesheetDataSerializer(WeeklyTimesheetDataSerializer):
    """Same structure of WeeklyTimesheetDataSerializer but for IMS context
    (substitutes staff_data for the IMS-specific serializer above)
    """

    staff_data = IMSWeeklyStaffDataSerializer(many=True)


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
