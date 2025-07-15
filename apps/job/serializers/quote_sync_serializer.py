"""
Serializers for Quote Sync Views.
"""

from rest_framework import serializers

from apps.job.serializers.costing_serializer import CostSetSerializer


class QuoteSyncErrorResponseSerializer(serializers.Serializer):
    """Serializer for quote sync error responses."""

    error = serializers.CharField()


class LinkQuoteSheetRequestSerializer(serializers.Serializer):
    """Serializer for link quote sheet request data."""

    template_url = serializers.URLField(required=False, allow_blank=True)


class LinkQuoteSheetResponseSerializer(serializers.Serializer):
    """Serializer for link quote sheet response."""

    sheet_url = serializers.URLField()
    sheet_id = serializers.CharField()
    job_id = serializers.CharField()


class DraftLineSerializer(serializers.Serializer):
    """Serializer for draft line data."""

    kind = serializers.CharField()
    desc = serializers.CharField()
    quantity = serializers.DecimalField(max_digits=10, decimal_places=2)
    unit_cost = serializers.DecimalField(max_digits=10, decimal_places=2)
    unit_rev = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_cost = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_rev = serializers.DecimalField(max_digits=10, decimal_places=2)


class QuoteChangesSerializer(serializers.Serializer):
    """Serializer for quote changes data."""

    additions = DraftLineSerializer(many=True)
    updates = DraftLineSerializer(many=True)
    deletions = DraftLineSerializer(many=True)


class PreviewQuoteResponseSerializer(serializers.Serializer):
    """Serializer for preview quote response."""

    # This will be flexible to accommodate the actual structure
    # from quote_sync_service.preview_quote()
    success = serializers.BooleanField(required=False)
    draft_lines = DraftLineSerializer(many=True, required=False)
    changes = QuoteChangesSerializer(required=False)
    message = serializers.CharField(required=False)

    # Allow additional fields that might come from the service
    class Meta:
        extra_kwargs = {"allow_extra_fields": True}


class ApplyQuoteResponseSerializer(serializers.Serializer):
    """Serializer for apply quote response."""

    success = serializers.BooleanField()
    cost_set = CostSetSerializer(required=False, allow_null=True)
    draft_lines = DraftLineSerializer(many=True, required=False)
    changes = QuoteChangesSerializer(required=False)
    error = serializers.CharField(required=False)


class ApplyQuoteErrorResponseSerializer(serializers.Serializer):
    """Serializer for apply quote error response."""

    success = serializers.BooleanField(default=False)
    error = serializers.CharField()
