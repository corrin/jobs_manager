"""
Daily Timesheet Serializers

DRF serializers for daily timesheet API endpoints
"""

from rest_framework import serializers


class JobBreakdownSerializer(serializers.Serializer):
    """Serializer for job breakdown data"""

    job_id = serializers.CharField()
    job_number = serializers.CharField()
    job_name = serializers.CharField()
    client = serializers.CharField()
    hours = serializers.FloatField()
    revenue = serializers.FloatField()
    cost = serializers.FloatField()
    is_billable = serializers.BooleanField()


class StaffDailyDataSerializer(serializers.Serializer):
    """Serializer for individual staff daily timesheet data"""

    staff_id = serializers.CharField()
    staff_name = serializers.CharField()
    staff_initials = serializers.CharField()
    avatar_url = serializers.CharField(allow_null=True)
    scheduled_hours = serializers.FloatField()
    actual_hours = serializers.FloatField()
    billable_hours = serializers.FloatField()
    non_billable_hours = serializers.FloatField()
    total_revenue = serializers.FloatField()
    total_cost = serializers.FloatField()
    status = serializers.CharField()
    status_class = serializers.CharField()
    billable_percentage = serializers.FloatField()
    completion_percentage = serializers.FloatField()
    job_breakdown = JobBreakdownSerializer(many=True)
    entry_count = serializers.IntegerField()
    alerts = serializers.ListField(child=serializers.CharField())


class DailyTotalsSerializer(serializers.Serializer):
    """Serializer for daily totals"""

    total_scheduled_hours = serializers.FloatField()
    total_actual_hours = serializers.FloatField()
    total_billable_hours = serializers.FloatField()
    total_non_billable_hours = serializers.FloatField()
    total_revenue = serializers.FloatField()
    total_cost = serializers.FloatField()
    total_entries = serializers.IntegerField()
    completion_percentage = serializers.FloatField()
    billable_percentage = serializers.FloatField()
    missing_hours = serializers.FloatField()


class SummaryStatsSerializer(serializers.Serializer):
    """Serializer for summary statistics"""

    total_staff = serializers.IntegerField()
    complete_staff = serializers.IntegerField()
    partial_staff = serializers.IntegerField()
    missing_staff = serializers.IntegerField()
    completion_rate = serializers.FloatField()


class DailyTimesheetSummarySerializer(serializers.Serializer):
    """Serializer for complete daily timesheet summary"""

    date = serializers.DateField()
    staff_data = StaffDailyDataSerializer(many=True)
    daily_totals = DailyTotalsSerializer()
    summary_stats = SummaryStatsSerializer()
