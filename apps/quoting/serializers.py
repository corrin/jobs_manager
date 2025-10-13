"""Serializers for quoting app REST APIs."""

from rest_framework import serializers


class SupplierPriceListUploadSerializer(serializers.Serializer):
    """Request serializer for supplier price list upload."""

    price_list_file = serializers.FileField(
        help_text="Supplier price list PDF file (max 10MB)"
    )
    duplicate_strategy = serializers.ChoiceField(
        choices=["skip", "update", "error"],
        required=False,
        default="skip",
        help_text="Strategy for handling duplicate products",
    )


class SupplierInfoSerializer(serializers.Serializer):
    """Supplier information in response."""

    name = serializers.CharField()
    id = serializers.UUIDField()
    created = serializers.BooleanField()


class PriceListInfoSerializer(serializers.Serializer):
    """Price list information in response."""

    id = serializers.UUIDField()
    filename = serializers.CharField()
    uploaded_at = serializers.DateTimeField()


class ImportStatisticsSerializer(serializers.Serializer):
    """Import statistics in response."""

    total_extracted = serializers.IntegerField()
    total_valid = serializers.IntegerField()
    imported = serializers.IntegerField()
    updated = serializers.IntegerField()
    skipped = serializers.IntegerField()
    failed = serializers.IntegerField()


class ValidationInfoSerializer(serializers.Serializer):
    """Validation warnings in response."""

    warnings = serializers.ListField(child=serializers.CharField())
    warning_count = serializers.IntegerField()


class ExtractSupplierPriceListResponseSerializer(serializers.Serializer):
    """Response serializer for supplier price list extraction."""

    success = serializers.BooleanField()
    message = serializers.CharField()
    supplier = SupplierInfoSerializer()
    price_list = PriceListInfoSerializer()
    statistics = ImportStatisticsSerializer()
    validation = ValidationInfoSerializer()


class ExtractSupplierPriceListErrorSerializer(serializers.Serializer):
    """Error response serializer for supplier price list extraction."""

    success = serializers.BooleanField()
    error = serializers.CharField()
    stage = serializers.CharField(required=False)
    validation_errors = serializers.ListField(
        child=serializers.CharField(), required=False
    )
    validation_warnings = serializers.ListField(
        child=serializers.CharField(), required=False
    )
