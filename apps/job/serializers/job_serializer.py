import logging

from rest_framework import serializers

from apps.accounting.models.invoice import Invoice
from apps.accounting.models.quote import Quote
from apps.client.models import Client, ClientContact
from apps.job.models import Job, JobFile

from .costing_serializer import CostSetSerializer, TimesheetCostLineSerializer
from .job_file_serializer import JobFileSerializer
from .quote_spreadsheet_serializer import QuoteSpreadsheetSerializer

logger = logging.getLogger(__name__)
DEBUG_SERIALIZER = False


class InvoiceSerializer(serializers.ModelSerializer):
    total_excl_tax = serializers.FloatField()
    total_incl_tax = serializers.FloatField()
    amount_due = serializers.FloatField()
    tax = serializers.FloatField(required=False)

    class Meta:
        model = Invoice
        fields = [
            "id",
            "xero_id",
            "number",
            "status",
            "date",
            "due_date",
            "total_excl_tax",
            "total_incl_tax",
            "amount_due",
            "tax",
            "online_url",
        ]


class QuoteSerializer(serializers.ModelSerializer):
    total_excl_tax = serializers.FloatField()
    total_incl_tax = serializers.FloatField()

    class Meta:
        model = Quote
        fields = [
            "id",
            "xero_id",
            "status",
            "date",
            "total_excl_tax",
            "total_incl_tax",
            "online_url",
        ]


class JobSerializer(serializers.ModelSerializer):
    # New CostSet fields (current system)
    latest_estimate = serializers.SerializerMethodField()
    latest_quote = serializers.SerializerMethodField()
    latest_actual = serializers.SerializerMethodField()
    quoted = serializers.BooleanField(read_only=True)
    invoiced = serializers.BooleanField(read_only=True)
    quote = serializers.SerializerMethodField()
    invoice = serializers.SerializerMethodField()

    client_id = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.all(),
        source="client",
        write_only=False,  # Allow read access
    )
    client_name = serializers.CharField(source="client.name", read_only=True)
    contact_id = serializers.PrimaryKeyRelatedField(
        queryset=ClientContact.objects.all(),
        source="contact",
        write_only=False,  # Allow read access
        required=False,
        allow_null=True,
    )
    contact_name = serializers.CharField(
        source="contact.name", read_only=True, required=False
    )
    job_status = serializers.CharField(source="status")
    job_files = JobFileSerializer(
        source="files", many=True, required=False
    )  # To prevent conflicts with PUTTING only one file

    # Quote spreadsheet relationship
    quote_sheet = QuoteSpreadsheetSerializer(read_only=True, required=False)

    def get_latest_estimate(self, obj) -> dict | None:
        """Get the latest estimate CostSet"""
        cost_set = obj.get_latest("estimate")
        return CostSetSerializer(cost_set).data if cost_set else None

    def get_latest_quote(self, obj) -> dict | None:
        """Get the latest quote CostSet"""
        cost_set = obj.get_latest("quote")
        return CostSetSerializer(cost_set).data if cost_set else None

    def get_latest_actual(self, obj) -> dict | None:
        """Get the latest actual CostSet"""
        cost_set = obj.get_latest("actual")
        return CostSetSerializer(cost_set).data if cost_set else None

    def get_quote(self, obj) -> dict | None:
        raw_quote = getattr(obj, "quote", None)
        logger.debug(f"Getting quote for job {obj.id}: {raw_quote} | {type(raw_quote)}")

        if raw_quote is not None:
            serialized = QuoteSerializer(raw_quote, context=self.context).data
            logger.debug(f"Serialized quote data: {serialized}")
            return serialized
        return None

    def get_invoice(self, obj) -> dict | None:
        raw_invoice = getattr(obj, "invoice", None)
        logger.debug(
            f"Getting invoice for job {obj.id}: {raw_invoice} | {type(raw_invoice)}"
        )

        if raw_invoice is not None:
            serialized = InvoiceSerializer(raw_invoice, context=self.context).data
            logger.debug(f"Serialized invoice data: {serialized}")
            return serialized
        return None

    class Meta:
        model = Job
        fields = [
            "id",
            "name",
            "client_id",
            "client_name",
            "contact_id",
            "contact_name",
            "job_number",
            "notes",
            "order_number",
            "created_at",
            "updated_at",
            "description",
            # New CostSet fields (current system)
            "latest_estimate",
            "latest_quote",
            "latest_actual",
            "job_status",
            "delivery_date",
            "paid",
            "quote_acceptance_date",
            "job_is_valid",
            "job_files",
            "charge_out_rate",
            "pricing_methodology",
            "quote_sheet",
            "quoted",
            "invoiced",
            "quote",
            "invoice",
            "shop_job",
        ]

    def validate(self, attrs):
        if DEBUG_SERIALIZER:
            logger.debug(f"JobSerializer validate called with attrs: {attrs}")

        # No longer validating pricing data - use CostSet/CostLine instead

        validated = super().validate(attrs)
        if DEBUG_SERIALIZER:
            logger.debug(f"After super().validate, data is: {validated}")
        return validated

    def update(self, instance, validated_data):
        logger.debug(f"JobSerializer update called for instance {instance.id}")
        logger.debug(f"Validated data received: {validated_data}")

        # Remove read-only/computed fields to avoid AttributeError
        validated_data.pop("quoted", None)
        validated_data.pop("invoiced", None)

        # Handle job files data first
        files_data = validated_data.pop("files", None)
        if files_data:
            for file_data in files_data:
                try:
                    job_file = JobFile.objects.get(id=file_data["id"], job=instance)
                    file_serializer = JobFileSerializer(
                        instance=job_file,
                        data=file_data,
                        partial=True,
                        context=self.context,
                    )
                    if file_serializer.is_valid():
                        file_serializer.save()
                    else:
                        logger.error(
                            f"JobFile validation failed: {file_serializer.errors}"
                        )
                        raise serializers.ValidationError(
                            {"job_files": file_serializer.errors}
                        )
                except JobFile.DoesNotExist:
                    logger.warning(
                        (
                            f"JobFile with id {file_data.get('id')} "
                            f"not found for job {instance.id}"
                        )
                    )
                except Exception as e:
                    logger.error(f"Error updating JobFile: {str(e)}")
                    raise serializers.ValidationError(f"Error updating file: {str(e)}")

        # Handle basic job fields
        for attr, value in validated_data.items():
            # Skip legacy pricing fields
            if attr not in [
                "latest_estimate_pricing",
                "latest_quote_pricing",
                "latest_reality_pricing",
            ]:
                setattr(instance, attr, value)

        # No longer processing pricing data - use CostSet/CostLine endpoints instead

        staff = self.context["request"].user if "request" in self.context else None
        instance.save(staff=staff)
        return instance


class CompleteJobSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.name", read_only=True)
    job_status = serializers.CharField(source="status")

    class Meta:
        model = Job
        fields = ["id", "job_number", "name", "client_name", "updated_at", "job_status"]


class JobCreateRequestSerializer(serializers.Serializer):
    """Serializer for job creation request data."""

    name = serializers.CharField(max_length=255)
    client_id = serializers.UUIDField()
    description = serializers.CharField(required=False, allow_blank=True)
    order_number = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    contact_id = serializers.UUIDField(required=False, allow_null=True)


class JobCreateResponseSerializer(serializers.Serializer):
    """Serializer for job creation response."""

    success = serializers.BooleanField(default=True)
    job_id = serializers.CharField()
    job_number = serializers.CharField()
    message = serializers.CharField()


class JobDetailResponseSerializer(serializers.Serializer):
    """Serializer for job detail response."""

    success = serializers.BooleanField(default=True)
    data = JobSerializer()


class JobRestErrorResponseSerializer(serializers.Serializer):
    """Serializer for job REST error responses."""

    error = serializers.CharField()


class JobDeleteResponseSerializer(serializers.Serializer):
    """Serializer for job deletion response."""

    success = serializers.BooleanField(default=True)
    message = serializers.CharField()


class AssignJobRequestSerializer(serializers.Serializer):
    """Serialiser for job assignment request"""

    job_id = serializers.CharField(help_text="Job ID")
    staff_id = serializers.CharField(help_text="Staff ID")


class AssignJobResponseSerializer(serializers.Serializer):
    """Serialiser for job assignment response"""

    success = serializers.BooleanField()
    message = serializers.CharField()


class ArchiveJobsRequestSerializer(serializers.Serializer):
    """Serialiser for job archiving request"""

    ids = serializers.ListField(
        child=serializers.CharField(), help_text="List of job IDs to archive"
    )


class ArchiveJobsResponseSerializer(serializers.Serializer):
    """Serialiser for job archiving response"""

    success = serializers.BooleanField()
    message = serializers.CharField(required=False)
    error = serializers.CharField(required=False)
    errors = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="List of specific errors",
    )


class WorkshopPDFResponseSerializer(serializers.Serializer):
    """Serializer for workshop PDF generation response"""

    # This endpoint returns a PDF file, so we use a simple error response serializer
    status = serializers.CharField(required=False, help_text="Response status")
    message = serializers.CharField(
        required=False, help_text="Error message if applicable"
    )

    class Meta:
        # This is primarily for documentation - the actual response is a
        # FileResponse (PDF)
        help_text = "Generates and returns a workshop PDF for the specified job"


class MonthEndJobHistorySerializer(serializers.Serializer):
    """Serializer for job history in month-end data"""

    date = serializers.DateField()
    total_hours = serializers.FloatField()
    total_dollars = serializers.FloatField()


class MonthEndJobSerializer(serializers.Serializer):
    """Serializer for special jobs in month-end processing"""

    job_id = serializers.UUIDField()
    job_number = serializers.CharField()
    job_name = serializers.CharField()
    client_name = serializers.CharField()
    history = MonthEndJobHistorySerializer(many=True)
    total_hours = serializers.FloatField()
    total_dollars = serializers.FloatField()


class MonthEndStockHistorySerializer(serializers.Serializer):
    """Serializer for stock job history in month-end data"""

    date = serializers.DateField()
    material_line_count = serializers.IntegerField()
    material_cost = serializers.FloatField()


class MonthEndStockJobSerializer(serializers.Serializer):
    """Serializer for stock job in month-end processing"""

    job_id = serializers.UUIDField()
    job_number = serializers.CharField()
    job_name = serializers.CharField()
    history = MonthEndStockHistorySerializer(many=True)


class MonthEndGetResponseSerializer(serializers.Serializer):
    """Serializer for month-end GET response"""

    jobs = MonthEndJobSerializer(many=True)
    stock_job = MonthEndStockJobSerializer()


class MonthEndPostRequestSerializer(serializers.Serializer):
    """Serializer for month-end POST request"""

    job_ids = serializers.ListField(
        child=serializers.UUIDField(),
        help_text="List of job IDs to process for month-end",
    )


class MonthEndPostResponseSerializer(serializers.Serializer):
    """Serializer for month-end POST response"""

    processed = serializers.ListField(
        child=serializers.UUIDField(),
        help_text="List of successfully processed job IDs",
    )
    errors = serializers.ListField(
        child=serializers.CharField(),
        help_text="List of error messages for failed processing",
    )


class MonthEndErrorResponseSerializer(serializers.Serializer):
    """Serializer for month-end error responses"""

    error = serializers.CharField(help_text="Error message")


# Modern Timesheet Serializers
class ModernTimesheetStaffSerializer(serializers.Serializer):
    """Serializer for staff information in timesheet responses"""

    id = serializers.UUIDField()
    name = serializers.CharField()
    firstName = serializers.CharField()
    lastName = serializers.CharField()


class ModernTimesheetSummarySerializer(serializers.Serializer):
    """Serializer for timesheet entry summary"""

    total_hours = serializers.FloatField()
    billable_hours = serializers.FloatField()
    non_billable_hours = serializers.FloatField()
    total_cost = serializers.FloatField()
    total_revenue = serializers.FloatField()
    entry_count = serializers.IntegerField()


class ModernTimesheetEntryGetResponseSerializer(serializers.Serializer):
    """Serializer for timesheet entry GET response"""

    cost_lines = serializers.ListField(
        child=serializers.DictField()
    )  # Accept list of dicts
    staff = ModernTimesheetStaffSerializer()
    date = serializers.DateField()
    summary = ModernTimesheetSummarySerializer()


class ModernTimesheetEntryPostRequestSerializer(serializers.Serializer):
    """Serializer for timesheet entry POST request"""

    job_id = serializers.UUIDField()
    staff_id = serializers.UUIDField()
    date = serializers.DateField()
    hours = serializers.FloatField(min_value=0)
    description = serializers.CharField(max_length=500)
    is_billable = serializers.BooleanField(default=True)
    hourly_rate = serializers.FloatField(min_value=0, required=False)


class ModernTimesheetEntryPostResponseSerializer(serializers.Serializer):
    """Serializer for timesheet entry POST response"""

    success = serializers.BooleanField()
    cost_line_id = serializers.UUIDField(required=False)
    message = serializers.CharField(required=False)


class ModernTimesheetJobGetResponseSerializer(serializers.Serializer):
    """Serializer for timesheet job GET response"""

    jobs = JobSerializer(many=True)
    total_count = serializers.IntegerField()


class ModernTimesheetDayGetResponseSerializer(serializers.Serializer):
    """Serializer for timesheet day GET response"""

    entries = TimesheetCostLineSerializer(many=True)
    summary = ModernTimesheetSummarySerializer()
    date = serializers.DateField()


class ModernTimesheetErrorResponseSerializer(serializers.Serializer):
    """Serializer for timesheet error responses"""

    error = serializers.CharField(help_text="Error message")


class JobEventCreateRequestSerializer(serializers.Serializer):
    """Serializer for job event creation request"""

    description = serializers.CharField(max_length=500)


class JobEventCreateResponseSerializer(serializers.Serializer):
    """Serializer for job event creation response"""

    success = serializers.BooleanField()
    event = serializers.DictField()


class WeeklyMetricsSerializer(serializers.Serializer):
    """Serializer for weekly metrics data"""

    job_id = serializers.UUIDField()
    job_number = serializers.IntegerField()
    name = serializers.CharField()
    client = serializers.CharField()
    description = serializers.CharField()
    status = serializers.CharField()
    people = serializers.ListField(
        child=serializers.DictField(),
    )
    estimated_hours = serializers.FloatField()
    actual_hours = serializers.FloatField()
    profit = serializers.FloatField()
