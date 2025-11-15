"""Serializers for data integrity report responses."""

from rest_framework import serializers


class BrokenFKReferenceSerializer(serializers.Serializer):
    """Details of a broken foreign key reference."""

    model = serializers.CharField(help_text="Model name")
    record_id = serializers.CharField(help_text="Record's UUID")
    field = serializers.CharField(help_text="FK field name")
    target_model = serializers.CharField(help_text="Target model that doesn't exist")
    target_id = serializers.CharField(help_text="Target UUID that doesn't exist")


class BrokenJSONReferenceSerializer(serializers.Serializer):
    """Details of a broken JSON field reference."""

    model = serializers.CharField(help_text="Model name")
    record_id = serializers.CharField(help_text="Record's UUID")
    field = serializers.CharField(help_text="JSON field path (e.g., meta.staff_id)")
    staff_id = serializers.CharField(
        required=False, allow_null=True, help_text="Invalid staff UUID"
    )
    stock_id = serializers.CharField(
        required=False, allow_null=True, help_text="Invalid stock UUID"
    )
    purchase_order_line_id = serializers.CharField(
        required=False, allow_null=True, help_text="Invalid PO line UUID"
    )
    issue = serializers.CharField(
        required=False, allow_null=True, help_text="Issue description"
    )


class BusinessRuleViolationSerializer(serializers.Serializer):
    """Details of a business rule violation."""

    model = serializers.CharField(help_text="Model name")
    record_id = serializers.CharField(help_text="Record's UUID")
    field = serializers.CharField(help_text="Field name")
    rule = serializers.CharField(help_text="Business rule that was violated")
    expected = serializers.CharField(
        required=False, allow_null=True, help_text="Expected value"
    )
    actual = serializers.CharField(
        required=False, allow_null=True, help_text="Actual value"
    )
    path = serializers.ListField(
        required=False,
        allow_null=True,
        child=serializers.CharField(),
        help_text="Path for circular references",
    )
    expected_path = serializers.CharField(
        required=False, allow_null=True, help_text="Expected file path"
    )


class DataIntegritySummarySerializer(serializers.Serializer):
    """Summary of data integrity scan results."""

    total_fk_checks = serializers.IntegerField(
        help_text="Number of FK relationships checked"
    )
    total_json_checks = serializers.IntegerField(
        help_text="Number of JSON references checked"
    )
    total_business_rule_checks = serializers.IntegerField(
        help_text="Number of business rules checked"
    )
    total_issues = serializers.IntegerField(help_text="Total issues found")


class DataIntegrityResponseSerializer(serializers.Serializer):
    """Response for data integrity scan."""

    scanned_at = serializers.DateTimeField(help_text="When the scan was performed")
    broken_fk_references = serializers.ListField(
        child=BrokenFKReferenceSerializer(),
        help_text="List of broken foreign key references",
    )
    broken_json_references = serializers.ListField(
        child=BrokenJSONReferenceSerializer(),
        help_text="List of broken JSON field references",
    )
    business_rule_violations = serializers.ListField(
        child=BusinessRuleViolationSerializer(),
        help_text="List of business rule violations",
    )
    summary = DataIntegritySummarySerializer(help_text="Summary statistics")
