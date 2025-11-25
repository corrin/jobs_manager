import logging
from decimal import Decimal
from pprint import pprint

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.accounts.models import Staff
from apps.job.models import CostLine, CostSet
from apps.workflow.models import CompanyDefaults

logger = logging.getLogger(__name__)


class CostLineSerializer(serializers.ModelSerializer):
    """
    Serializer for CostLine model - read-only with basic depth
    """

    total_cost = serializers.SerializerMethodField()
    total_rev = serializers.SerializerMethodField()

    class Meta:
        model = CostLine
        fields = [
            "id",
            "kind",
            "desc",
            "quantity",
            "unit_cost",
            "unit_rev",
            "total_cost",
            "total_rev",
            "accounting_date",
            "ext_refs",
            "meta",
            "created_at",
            "updated_at",
        ]

    def get_total_cost(self, obj) -> float:
        """Get total cost (quantity * unit_cost)"""
        return float(obj.total_cost)

    def get_total_rev(self, obj) -> float:
        """Get total revenue (quantity * unit_rev)"""
        return float(obj.total_rev)


class TimesheetCostLineSerializer(serializers.ModelSerializer):
    """
    Serializer for CostLine model specifically for timesheet entries

    Architecture principle: Job data comes from CostSet->Job relationship,
    NOT from metadata. This ensures data consistency and follows SRP:
    - Metadata = timesheet-specific data (staff, date, billable, etc.)
    - Relationship = job data (job_id, job_number, job_name, client)

    Benefits:
    - No data duplication
    - Always consistent with source Job
    - Simplified queries and maintenance
    """

    total_cost = serializers.SerializerMethodField()
    total_rev = serializers.SerializerMethodField()

    # Job information from CostSet relationship (NOT from metadata)
    job_id = serializers.CharField(source="cost_set.job.id", read_only=True)
    job_number = serializers.IntegerField(
        source="cost_set.job.job_number", read_only=True
    )
    job_name = serializers.CharField(source="cost_set.job.name", read_only=True)
    charge_out_rate = serializers.DecimalField(
        source="cost_set.job.charge_out_rate",
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )

    # Client name with null handling
    client_name = serializers.SerializerMethodField()

    # Staff wage rate for frontend cost calculations
    wage_rate = serializers.SerializerMethodField()

    def get_total_cost(self, obj) -> float:
        """Get total cost (quantity * unit_cost)"""
        return float(obj.quantity * obj.unit_cost) if obj.unit_cost else 0.0

    def get_total_rev(self, obj) -> float:
        """Get total revenue (quantity * unit_rev)"""
        return float(obj.quantity * obj.unit_rev) if obj.unit_rev else 0.0

    def get_client_name(self, obj) -> str:
        """Get client name with safe null handling"""
        if obj.cost_set and obj.cost_set.job and obj.cost_set.job.client:
            return obj.cost_set.job.client.name
        return ""

    def get_wage_rate(self, obj) -> float:
        """Get staff wage rate from metadata staff_id"""
        try:
            # Get staff_id from metadata
            staff_id = obj.meta.get("staff_id") if obj.meta else None
            if not staff_id:
                return 0.0

            # Get staff and return wage_rate
            staff = Staff.objects.get(id=staff_id)
            return float(staff.wage_rate) if staff.wage_rate else 0.0

        except (Staff.DoesNotExist, ValueError, AttributeError):
            return 0.0

    class Meta:
        model = CostLine
        fields = [
            "id",
            "kind",
            "desc",
            "quantity",
            "unit_cost",
            "unit_rev",
            "total_cost",
            "total_rev",
            "accounting_date",
            "ext_refs",
            "meta",
            "created_at",
            "updated_at",
            "job_id",
            "job_number",
            "job_name",
            "client_name",
            "charge_out_rate",
            "wage_rate",
        ]
        read_only_fields = fields


class CostLineCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for CostLine creation and updates - full write capabilities
    """

    class Meta:
        model = CostLine
        fields = [
            "kind",
            "desc",
            "quantity",
            "unit_cost",
            "unit_rev",
            "accounting_date",
            "ext_refs",
            "meta",
            "created_at",
            "updated_at",
        ]

    def validate(self, data):
        """Custom validation with detailed logging"""
        logger.info(f"Validating CostLine data: {data}")
        return super().validate(data)

    def validate_quantity(self, value):
        """Validate quantity is non-negative"""
        logger.info(f"Validating quantity: {value} (type: {type(value)})")
        if value < 0:
            raise serializers.ValidationError("Quantity must be non-negative")
        return value

    def validate_unit_cost(self, value):
        """Validate unit cost - allow negative values for adjustments"""
        logger.info(f"Validating unit_cost: {value} (type: {type(value)})")
        # Allow negative values for adjustments, discounts, credits
        return value

    def validate_unit_rev(self, value):
        """Validate unit revenue - allow negative values for adjustments"""
        logger.info(f"Validating unit_rev: {value} (type: {type(value)})")
        # Allow negative values for adjustments, discounts, credits
        return value

    def save(self, **kwargs):
        """Override save to auto-calculate unit_cost and unit_rev for timesheet entries"""
        # Check if this is a timesheet entry
        meta = self.validated_data.get("meta", {})
        kind = self.validated_data.get("kind")

        if kind == "time" and meta.get("created_from_timesheet"):
            line_id = self.validated_data.get("id")
            logger.info(f"Starting to autocalculate unit cost for cost line {line_id}")
            pprint(self.validated_data)
            # Auto-calculate unit_cost from staff wage_rate and rate multiplier
            staff_id = meta.get("staff_id")

            if not staff_id:
                exception = serializers.ValidationError(
                    "Staff id must be provided when creating a new timesheet entry."
                )
                raise exception

            try:
                staff = Staff.objects.get(id=staff_id)
                company_defaults = CompanyDefaults.objects.first()

                # Use staff wage_rate or company default
                wage_rate = (
                    staff.wage_rate if staff.wage_rate else company_defaults.wage_rate
                )

                rate_multiplier = Decimal(meta.get("rate_multiplier", None))
                if rate_multiplier is None:
                    exception = serializers.ValidationError(
                        "Rate multiplier must be provided when creating a new timesheet entry."
                    )
                    raise exception

                final_wage = wage_rate * rate_multiplier
                self.validated_data["unit_cost"] = final_wage
                logger.info(
                    f"Auto-calculated unit_cost: {final_wage} for staff {staff_id}"
                )

            except Staff.DoesNotExist:
                logger.warning(f"Staff not found: {staff_id}")
            except Exception as e:
                logger.error(f"Error calculating unit_cost: {e}")

            # Auto-calculate unit_rev from job charge_out_rate
            if hasattr(self, "instance") and self.instance and self.instance.cost_set:
                job = self.instance.cost_set.job
                is_billable = meta.get("is_billable", False)
                if job and job.charge_out_rate and is_billable:
                    self.validated_data["unit_rev"] = job.charge_out_rate

                    logger.info(
                        f"Auto-calculated unit_rev: {job.charge_out_rate} from job {job.job_number}"
                    )
                else:
                    self.validated_data["unit_rev"] = Decimal("0.0")
                    logger.info(
                        "Auto-calculated unit_rev is 0 because entry is not billable"
                    )

        return super().save(**kwargs)


class CostSetSummarySerializer(serializers.Serializer):
    """
    Serializer for CostSet summary data - used in cost analysis
    """

    cost = serializers.FloatField(help_text="Total cost for this cost set")
    rev = serializers.FloatField(help_text="Total revenue for this cost set")
    hours = serializers.FloatField(help_text="Total hours for this cost set")
    profitMargin = serializers.SerializerMethodField(
        help_text="Calculated profit margin percentage"
    )

    def get_profitMargin(self, obj) -> float:
        """Calculate profit margin as a percentage"""
        rev = obj.get("rev", 0)
        cost = obj.get("cost", 0)
        if rev > 0:
            return ((rev - cost) / rev) * 100
        return 0.0


class CostSetSerializer(serializers.ModelSerializer):
    """
    Serializer for CostSet model - includes nested cost lines
    """

    cost_lines = CostLineSerializer(many=True, read_only=True)
    summary = serializers.SerializerMethodField()
    id = serializers.CharField(read_only=True)  # UUID as string

    @extend_schema_field(CostSetSummarySerializer)
    def get_summary(self, obj):
        """Get summary data for this cost set"""
        return obj.summary

    def to_representation(self, instance):
        data = super().to_representation(instance)

        # Check for missing summary data - log error but don't crash frontend
        summary = data.get("summary")
        if not summary:
            ValueError(f"CostSet {instance.id} missing required summary data")
            logger.error(f"CostSet {instance.id} missing summary data")
            # Return minimal safe structure
            data["summary"] = {"cost": 0, "rev": 0, "hours": 0, "profitMargin": 0.0}
            return data

        # Calculate profit margin
        rev = summary.get("rev", 0)
        cost = summary.get("cost", 0)
        if rev > 0:
            summary["profitMargin"] = ((rev - cost) / rev) * 100
        else:
            summary["profitMargin"] = 0.0

        data["summary"] = summary
        return data

    class Meta:
        model = CostSet
        fields = ["id", "kind", "rev", "summary", "created", "cost_lines"]
        read_only_fields = fields


class CostLineErrorResponseSerializer(serializers.Serializer):
    """Serializer for cost line error responses."""

    error = serializers.CharField()


class CostLineCreateResponseSerializer(serializers.Serializer):
    """Serializer for cost line creation success response."""

    # Uses the full CostLineSerializer data structure
    id = serializers.CharField()
    kind = serializers.CharField()
    desc = serializers.CharField()
    quantity = serializers.DecimalField(max_digits=10, decimal_places=2)
    unit_cost = serializers.DecimalField(max_digits=10, decimal_places=2)
    unit_rev = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_cost = serializers.ReadOnlyField()
    total_rev = serializers.ReadOnlyField()
    accounting_date = serializers.DateField()
    ext_refs = serializers.JSONField(required=False)
    meta = serializers.JSONField(required=False)


class QuoteImportStatusResponseSerializer(serializers.Serializer):
    """Serializer for quote import status response"""

    job_id = serializers.CharField()
    job_name = serializers.CharField()
    has_quote = serializers.BooleanField()
    quote = CostSetSerializer(required=False)
    revision = serializers.IntegerField(required=False)
    created = serializers.DateTimeField(required=False)
    summary = serializers.JSONField(required=False)


class QuoteRevisionRequestSerializer(serializers.Serializer):
    """Serializer for quote revision request - validates input data"""

    reason = serializers.CharField(
        max_length=500,
        required=False,
        help_text="Optional reason for creating a new quote revision",
    )


class QuoteRevisionResponseSerializer(serializers.Serializer):
    """Serializer for quote revision response"""

    success = serializers.BooleanField()
    message = serializers.CharField()
    quote_revision = serializers.IntegerField()
    archived_cost_lines_count = serializers.IntegerField()
    job_id = serializers.CharField()

    # Optional error details
    error = serializers.CharField(required=False)


class QuoteRevisionsListSerializer(serializers.Serializer):
    """Serializer for listing quote revisions"""

    job_id = serializers.CharField()
    job_number = serializers.IntegerField()
    current_cost_set_rev = serializers.IntegerField()
    total_revisions = serializers.IntegerField()
    revisions = serializers.ListField(
        child=serializers.DictField(),
        help_text="List of archived quote revisions with their data",
    )
