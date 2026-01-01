"""
Xero Payroll Serializers

DRF serializers for Xero Payroll API endpoints
"""

from rest_framework import serializers


class CreatePayRunSerializer(serializers.Serializer):
    """Request serializer for creating a pay run"""

    week_start_date = serializers.DateField(help_text="Monday of the week (YYYY-MM-DD)")


class CreatePayRunResponseSerializer(serializers.Serializer):
    """Response serializer for created pay run"""

    id = serializers.UUIDField(help_text="Django primary key")
    xero_id = serializers.UUIDField(help_text="Xero pay run ID")
    status = serializers.CharField()
    period_start_date = serializers.DateField()
    period_end_date = serializers.DateField()
    payment_date = serializers.DateField()


class PostWeekToXeroSerializer(serializers.Serializer):
    """Request serializer for posting weekly timesheets to Xero"""

    staff_ids = serializers.ListField(
        child=serializers.UUIDField(),
        help_text="List of staff member UUIDs",
    )
    week_start_date = serializers.DateField(help_text="Monday of the week (YYYY-MM-DD)")


class PostWeekToXeroResponseSerializer(serializers.Serializer):
    """Response serializer for posted timesheet"""

    success = serializers.BooleanField()
    xero_timesheet_id = serializers.CharField(allow_null=True)
    xero_leave_ids = serializers.ListField(
        child=serializers.CharField(), allow_null=True, allow_empty=True, required=False
    )
    entries_posted = serializers.IntegerField()
    work_hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    other_leave_hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    leave_hours = serializers.DecimalField(max_digits=10, decimal_places=2)
    errors = serializers.ListField(child=serializers.CharField())


class PayRunDetailsSerializer(serializers.Serializer):
    """Serializer representing details from a Xero pay run."""

    id = serializers.UUIDField(help_text="Django primary key")
    xero_id = serializers.UUIDField(help_text="Xero pay run ID")
    payroll_calendar_id = serializers.CharField(allow_null=True)
    period_start_date = serializers.DateField()
    period_end_date = serializers.DateField()
    payment_date = serializers.DateField()
    pay_run_status = serializers.CharField()
    pay_run_type = serializers.CharField(allow_null=True)


class PayRunForWeekResponseSerializer(serializers.Serializer):
    """Response serializer when fetching pay run data for a week."""

    exists = serializers.BooleanField()
    pay_run = PayRunDetailsSerializer(allow_null=True)
    warning = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class PayRunSyncResponseSerializer(serializers.Serializer):
    """Response payload after refreshing cached pay runs."""

    synced = serializers.BooleanField()
    fetched = serializers.IntegerField(help_text="Number of pay runs fetched from Xero")
    created = serializers.IntegerField(
        help_text="Number of new pay runs created locally"
    )
    updated = serializers.IntegerField(help_text="Number of existing pay runs updated")
