import logging

from rest_framework import serializers

from apps.job.models import CostLine, CostSet

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
            "ext_refs",
            "meta",
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
    job_number = serializers.CharField(source="cost_set.job.job_number", read_only=True)
    job_name = serializers.CharField(source="cost_set.job.name", read_only=True)
    charge_out_rate = serializers.DecimalField(
        source="cost_set.job.charge_out_rate",
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )

    # Client name with null handling
    client_name = serializers.SerializerMethodField()

    def get_total_cost(self, obj) -> float:
        """Get total cost (quantity * unit_cost)"""
        return float(obj.total_cost)

    def get_total_rev(self, obj) -> float:
        """Get total revenue (quantity * unit_rev)"""
        return float(obj.total_rev)

    def get_client_name(self, obj) -> str:
        """Get client name with safe null handling"""
        if obj.cost_set and obj.cost_set.job and obj.cost_set.job.client:
            return obj.cost_set.job.client.name
        return ""

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
            "ext_refs",
            "meta",
            "job_id",
            "job_number",
            "job_name",
            "client_name",
            "charge_out_rate",
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
            "ext_refs",
            "meta",
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
        """Validate unit cost is non-negative"""
        logger.info(f"Validating unit_cost: {value} (type: {type(value)})")
        if value < 0:
            raise serializers.ValidationError("Unit cost must be non-negative")
        return value

    def validate_unit_rev(self, value):
        """Validate unit revenue is non-negative"""
        logger.info(f"Validating unit_rev: {value} (type: {type(value)})")
        if value < 0:
            raise serializers.ValidationError("Unit revenue must be non-negative")
        return value


class CostSetSerializer(serializers.ModelSerializer):
    """
    Serializer for CostSet model - includes nested cost lines
    """

    cost_lines = CostLineSerializer(many=True, read_only=True)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Ensures that summary always contains the required fields
        summary = data.get("summary") or {}
        data["summary"] = {
            "cost": summary.get("cost", 0),
            "rev": summary.get("rev", 0),
            "hours": summary.get("hours", 0),
        }
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
