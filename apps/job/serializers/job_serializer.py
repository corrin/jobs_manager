import logging

from django.core.exceptions import ObjectDoesNotExist
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.accounting.models.invoice import Invoice
from apps.accounting.models.quote import Quote
from apps.client.models import Client, ClientContact
from apps.job.models import Job, JobEvent, JobFile

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


# Front-end uses "quote" field with financial data being displayed.
# This is useless for front-end currently, we use all information from above.
# Since I didn't get the specific requirements for this, I'll just ignore and keep using the original serializer.
class XeroQuoteSerializer(serializers.ModelSerializer):
    """Simplified Quote serializer for xero_quote field"""

    class Meta:
        model = Quote
        fields = ["status", "online_url"]


# Same for this.
class XeroInvoiceSerializer(serializers.ModelSerializer):
    """Simplified Invoice serializer for xero_invoices field"""

    class Meta:
        model = Invoice
        fields = ["number", "status", "online_url"]


class CompanyDefaultsJobDetailSerializer(serializers.Serializer):
    """Serializer for company defaults in job detail response"""

    materials_markup = serializers.FloatField(
        help_text="Default markup percentage for materials"
    )
    time_markup = serializers.FloatField(help_text="Default markup percentage for time")
    charge_out_rate = serializers.FloatField(
        help_text="Default charge-out rate for staff"
    )
    wage_rate = serializers.FloatField(help_text="Default wage rate for staff")


class JobSerializer(serializers.ModelSerializer):
    # New CostSet fields (current system)
    latest_estimate = serializers.SerializerMethodField()
    latest_quote = serializers.SerializerMethodField()
    latest_actual = serializers.SerializerMethodField()
    quoted = serializers.BooleanField(read_only=True)
    fully_invoiced = serializers.BooleanField(read_only=True)
    quote = serializers.SerializerMethodField()
    invoices = serializers.SerializerMethodField()

    # CURRENTLY UNUSED/UNUSEFUL FOR FE:
    xero_quote = serializers.SerializerMethodField()
    xero_invoices = serializers.SerializerMethodField()

    client_id = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.all(),
        source="client",
        write_only=False,  # Allow read access,
        allow_null=True,
        required=False,
    )
    # Some clients might not exist in old production data, so for compatibility we allow null values for it (unrequired, allow_null=True)
    client_name = serializers.CharField(
        source="client.name", read_only=True, allow_null=True, required=False
    )
    contact_id = serializers.PrimaryKeyRelatedField(
        queryset=ClientContact.objects.all(),
        source="contact",
        write_only=False,  # Allow read access
        required=False,
        allow_null=True,
    )
    contact_name = serializers.CharField(
        source="contact.name", read_only=True, required=False, allow_null=True
    )
    job_status = serializers.CharField(source="status")
    job_files = JobFileSerializer(
        source="files", many=True, required=False
    )  # To prevent conflicts with PUTTING only one file

    # Quote spreadsheet relationship
    quote_sheet = QuoteSpreadsheetSerializer(
        read_only=True, required=False, allow_null=True
    )

    @extend_schema_field(CostSetSerializer)
    def get_latest_estimate(self, obj) -> dict | None:
        """Get the latest estimate CostSet"""
        cost_set = obj.get_latest("estimate")
        return CostSetSerializer(cost_set).data if cost_set else None

    @extend_schema_field(CostSetSerializer)
    def get_latest_quote(self, obj) -> dict | None:
        """Get the latest quote CostSet"""
        cost_set = obj.get_latest("quote")
        return CostSetSerializer(cost_set).data if cost_set else None

    @extend_schema_field(CostSetSerializer)
    def get_latest_actual(self, obj) -> dict | None:
        """Get the latest actual CostSet"""
        cost_set = obj.get_latest("actual")
        return CostSetSerializer(cost_set).data if cost_set else None

    @extend_schema_field(QuoteSerializer(allow_null=True))
    def get_quote(self, obj) -> dict | None:
        """Get Xero quote information"""
        try:
            return QuoteSerializer(obj.quote).data
        except ObjectDoesNotExist:
            return None

    @extend_schema_field(InvoiceSerializer(many=True))
    def get_invoices(self, obj) -> list[dict]:
        """Get Xero invoices information"""
        return InvoiceSerializer(obj.invoices.all(), many=True).data

    @extend_schema_field(XeroQuoteSerializer(allow_null=True))
    def get_xero_quote(self, obj) -> dict | None:
        """Get Xero quote information (status and URL only)"""
        try:
            return XeroQuoteSerializer(obj.quote).data
        except ObjectDoesNotExist:
            return None

    @extend_schema_field(XeroInvoiceSerializer(many=True))
    def get_xero_invoices(self, obj) -> list[dict]:
        """Get Xero invoices information (number, status, and URL only)"""
        return XeroInvoiceSerializer(obj.invoices.all(), many=True).data

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
            "fully_invoiced",
            "quote",
            "invoices",
            "xero_quote",
            "xero_invoices",
            "shop_job",
        ]

    def validate(self, attrs):
        if DEBUG_SERIALIZER:
            logger.debug(f"JobSerializer validate called with attrs: {attrs}")

        # Validate contact belongs to client
        contact = attrs.get("contact")
        client = attrs.get("client")

        # If we're updating and no client is provided, use the existing client
        if not client and self.instance:
            client = self.instance.client

        if contact and client:
            logger.debug(
                f"JobSerializer validate - Checking if contact {contact.id} belongs to client {client.id}"
            )
            if contact.client != client:
                logger.error(
                    f"JobSerializer validate - Contact {contact.id} does not belong to client {client.id}"
                )
                raise serializers.ValidationError(
                    {
                        "contact_id": f"Contact does not belong to the selected client. Contact belongs to {contact.client.name}, but job is for {client.name}."
                    }
                )
            if DEBUG_SERIALIZER:
                logger.debug(
                    f"JobSerializer validate - Contact {contact.id} belongs to client {client.id}"
                )
                logger.debug("JobSerializer validate - Contact validation passed")

        # No longer validating pricing data - use CostSet/CostLine instead

        validated = super().validate(attrs)
        if DEBUG_SERIALIZER:
            logger.debug(f"After super().validate, data is: {validated}")
        return validated

    def update(self, instance, validated_data):
        logger.debug(f"JobSerializer update called for instance {instance.id}")
        logger.debug(f"Validated data received: {validated_data}")

        # DEBUG: Log contact-related data specifically
        contact_obj = validated_data.get("contact")
        logger.debug(f"JobSerializer update - contact in validated_data: {contact_obj}")
        logger.debug(
            f"JobSerializer update - current instance contact: {instance.contact}"
        )

        # Remove read-only/computed fields to avoid AttributeError
        validated_data.pop("quoted", None)
        validated_data.pop("fully_invoiced", None)

        # Handle job files data first
        files_data = validated_data.pop("files", None)
        if files_data:
            existing = {f.id: f for f in instance.files.all()}
            for file_data in files_data:
                file_id = file_data[
                    "id"
                ]  # No need for double validation, DRF ensures this already

                if file_id not in existing:
                    JobFile.objects.create(
                        job=instance,
                        **file_data,
                    )
                    continue

                job_file = existing[file_id]
                serializer = JobFileSerializer(
                    instance=job_file,
                    data=file_data,
                    partial=True,
                    context=self.context,
                )
                serializer.is_valid(raise_exception=True)
                serializer.save()

        # Handle basic job fields
        for attr, value in validated_data.items():
            # Skip legacy pricing fields
            if attr not in [
                "latest_estimate_pricing",
                "latest_quote_pricing",
                "latest_reality_pricing",
            ]:
                logger.debug(f"JobSerializer update - Setting {attr} = {value}")
                setattr(instance, attr, value)

        # DEBUG: Log contact after setting attributes
        logger.debug(
            f"JobSerializer update - instance contact after setattr: {instance.contact}"
        )

        # Special handling for contact field to ensure it's properly set
        if "contact" in validated_data:
            contact_value = validated_data["contact"]
            logger.debug(
                f"JobSerializer update - Explicitly setting contact to: {contact_value}"
            )
            instance.contact = contact_value
            logger.debug(
                f"JobSerializer update - Contact after explicit set: {instance.contact}"
            )

        # No longer processing pricing data - use CostSet/CostLine endpoints instead

        staff = self.context["request"].user if "request" in self.context else None
        instance.save(staff=staff)

        # DEBUG: Log contact after save
        logger.debug(
            f"JobSerializer update - instance contact after save: {instance.contact}"
        )

        return instance


class JobQuoteAcceptanceSerializer(serializers.Serializer):
    """Serializer for job quote acceptance data."""

    success = serializers.BooleanField()
    job_id = serializers.UUIDField()
    quote_acceptance_date = serializers.CharField()
    message = serializers.CharField()


class JobEventSerializer(serializers.ModelSerializer):
    """Serializer for JobEvent model - read-only for frontend consumption

    Merged from duplicate definition - uses get_display_full_name for better
    staff display (respects preferred names vs just first_name)
    """

    staff = serializers.CharField(
        source="staff.get_display_full_name",
        read_only=True,
        allow_null=True,
        required=False,
    )
    timestamp = serializers.DateTimeField(read_only=True)

    class Meta:
        model = JobEvent
        fields = ["id", "description", "timestamp", "staff", "event_type"]
        read_only_fields = fields


class JobDataSerializer(serializers.Serializer):
    job = JobSerializer()
    events = JobEventSerializer(many=True, read_only=True)
    company_defaults = CompanyDefaultsJobDetailSerializer(read_only=True)


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
    pricing_methodology = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )


class JobCreateResponseSerializer(serializers.Serializer):
    """Serializer for job creation response."""

    success = serializers.BooleanField(default=True)
    job_id = serializers.CharField()
    job_number = serializers.IntegerField()
    message = serializers.CharField()


class JobDetailResponseSerializer(serializers.Serializer):
    """Serializer for job detail response."""

    success = serializers.BooleanField(default=True)
    data = JobDataSerializer()


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
    job_number = serializers.IntegerField()
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
    job_number = serializers.IntegerField()
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

    cost_lines = TimesheetCostLineSerializer(many=True)
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
    event = JobEventSerializer()


class WeeklyMetricsSerializer(serializers.Serializer):
    """Serializer for weekly metrics data"""

    job_id = serializers.UUIDField()
    job_number = serializers.IntegerField()
    name = serializers.CharField()
    client = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    description = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    status = serializers.CharField()
    people = serializers.ListField(
        child=serializers.DictField(),
    )
    estimated_hours = serializers.FloatField()
    actual_hours = serializers.FloatField()
    profit = serializers.FloatField()


# JobView Enhancement Serializers


class JobClientHeaderSerializer(serializers.Serializer):
    """Serializer for client data in job header response"""

    id = serializers.UUIDField()
    name = serializers.CharField()


class JobHeaderResponseSerializer(serializers.Serializer):
    """Serializer for job header response - essential job data for fast loading"""

    job_id = serializers.UUIDField()
    job_number = serializers.IntegerField()
    name = serializers.CharField()
    client = JobClientHeaderSerializer()
    status = serializers.CharField()
    pricing_methodology = serializers.CharField(allow_null=True)
    fully_invoiced = serializers.BooleanField()
    quoted = serializers.BooleanField()
    quote_acceptance_date = serializers.DateTimeField(allow_null=True)
    paid = serializers.BooleanField()


class JobStatusChoicesResponseSerializer(serializers.Serializer):
    """Serializer for job status choices response"""

    statuses = serializers.DictField()


class JobInvoicesResponseSerializer(serializers.Serializer):
    """Serializer for job invoices response"""

    invoices = InvoiceSerializer(many=True)


class JobCostSetSummarySerializer(serializers.Serializer):
    """Serializer for cost set summary data in job views"""

    cost = serializers.FloatField()
    rev = serializers.FloatField()
    hours = serializers.FloatField()
    profitMargin = serializers.FloatField(allow_null=True)


class JobCostSummaryResponseSerializer(serializers.Serializer):
    """Serializer for job cost summary response"""

    estimate = JobCostSetSummarySerializer(allow_null=True)
    quote = JobCostSetSummarySerializer(allow_null=True)
    actual = JobCostSetSummarySerializer(allow_null=True)


class JobEventsResponseSerializer(serializers.Serializer):
    """Serializer for job events response"""

    events = JobEventSerializer(many=True)


class JobBasicInformationResponseSerializer(serializers.Serializer):
    """Serializer for job basic information response"""

    description = serializers.CharField(allow_blank=True, allow_null=True)
    delivery_date = serializers.DateField(allow_null=True)
    order_number = serializers.CharField(allow_blank=True, allow_null=True)
    notes = serializers.CharField(allow_blank=True, allow_null=True)


class JobPatchRequestSerializer(serializers.Serializer):
    """Serializer for job PATCH request - all updatable fields are optional"""

    # Basic job information
    name = serializers.CharField(
        max_length=100, required=False, allow_blank=False, help_text="Job name"
    )
    description = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, help_text="Job description"
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Internal notes about the job",
    )
    order_number = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text="Order number",
    )

    # Status and workflow
    job_status = serializers.ChoiceField(
        choices=Job.JOB_STATUS_CHOICES, required=False, help_text="Job status"
    )
    paid = serializers.BooleanField(
        required=False, help_text="Whether the job has been paid"
    )
    job_is_valid = serializers.BooleanField(
        required=False, help_text="Whether the job is valid"
    )

    # Dates
    delivery_date = serializers.DateField(
        required=False, allow_null=True, help_text="Delivery date"
    )
    quote_acceptance_date = serializers.DateTimeField(
        required=False, allow_null=True, help_text="Quote acceptance date"
    )

    # Financial
    charge_out_rate = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        allow_null=False,
        help_text="Charge out rate",
    )
    pricing_methodology = serializers.ChoiceField(
        choices=Job.PRICING_METHODOLOGY_CHOICES,
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text="Pricing methodology",
    )

    # Relationships (only IDs, no derived names)
    client_id = serializers.UUIDField(
        required=False, allow_null=True, help_text="Client ID"
    )
    contact_id = serializers.UUIDField(
        required=False, allow_null=True, help_text="Contact person ID"
    )

    # Files
    job_files = serializers.ListField(
        child=serializers.DictField(), required=False, help_text="Job files"
    )

    def validate_client_id(self, value):
        """Validate that client exists if provided"""
        if value:
            try:
                Client.objects.get(id=value)
            except Client.DoesNotExist:
                raise serializers.ValidationError("Client not found")
        return value

    def validate_contact_id(self, value):
        """Validate that contact exists if provided"""
        if value:
            try:
                ClientContact.objects.get(id=value)
            except ClientContact.DoesNotExist:
                raise serializers.ValidationError("Contact not found")
        return value

    def validate(self, attrs):
        """Cross-field validation"""
        # Validate contact belongs to client if both are provided
        contact_id = attrs.get("contact_id")
        client_id = attrs.get("client_id")

        if contact_id and client_id:
            try:
                contact = ClientContact.objects.get(id=contact_id)
                client = Client.objects.get(id=client_id)
                if contact.client != client:
                    raise serializers.ValidationError(
                        {"contact_id": "Contact does not belong to the selected client"}
                    )
            except (ClientContact.DoesNotExist, Client.DoesNotExist):
                pass  # Individual field validation will catch these

        return attrs
