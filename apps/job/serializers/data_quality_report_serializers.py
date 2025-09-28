"""Serializers for data quality report responses."""

from rest_framework import serializers


class ComplianceSummarySerializer(serializers.Serializer):
    """Summary of compliance issues."""

    not_invoiced = serializers.IntegerField(
        help_text="Number of jobs that are not invoiced"
    )
    not_paid = serializers.IntegerField(help_text="Number of jobs that are not paid")
    not_cancelled = serializers.IntegerField(
        help_text="Number of jobs that should be cancelled but are not"
    )
    has_open_tasks = serializers.IntegerField(
        help_text="Number of jobs with open tasks"
    )


class ArchivedJobIssueSerializer(serializers.Serializer):
    """Details of a non-compliant archived job."""

    job_id = serializers.CharField(help_text="Job's unique identifier")
    job_number = serializers.CharField(help_text="Job number")
    client_name = serializers.CharField(help_text="Client name or 'Shop Job'")
    archived_date = serializers.DateField(help_text="Date when job was archived")
    current_status = serializers.CharField(help_text="Job's current status")
    issue = serializers.CharField(
        help_text="Compliance issue: 'Not invoiced', 'Not paid', 'Not cancelled', 'Has open tasks'"
    )
    invoice_status = serializers.CharField(
        required=False, allow_null=True, help_text="Invoice status if relevant"
    )
    outstanding_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        allow_null=True,
        help_text="Outstanding amount if relevant",
    )


class ArchivedJobsComplianceResponseSerializer(serializers.Serializer):
    """Response for archived jobs compliance check."""

    total_archived_jobs = serializers.IntegerField(
        help_text="Total number of archived jobs"
    )
    non_compliant_jobs = serializers.ListField(
        child=ArchivedJobIssueSerializer(),
        help_text="List of non-compliant jobs with details",
    )
    summary = ComplianceSummarySerializer(help_text="Summary of compliance issues")
    checked_at = serializers.DateTimeField(help_text="When the check was performed")
