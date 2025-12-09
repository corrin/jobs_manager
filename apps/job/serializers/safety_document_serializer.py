"""
Serializers for SafetyDocument (JSA/SWP) API endpoints.

Document content is stored in Google Docs - these serializers handle
metadata and the Google Doc reference.
"""

from rest_framework import serializers

from apps.job.models import SafetyDocument


class SafetyDocumentSerializer(serializers.ModelSerializer):
    """
    Main serializer for SafetyDocument model.

    Returns document metadata and Google Docs URL for editing.
    """

    job_id = serializers.UUIDField(
        source="job.id",
        read_only=True,
        allow_null=True,
        help_text="Linked job ID (null for SWPs)",
    )
    job_number = serializers.CharField(
        source="job.job_number",
        read_only=True,
        allow_null=True,
        help_text="Linked job number (null for SWPs)",
    )

    class Meta:
        model = SafetyDocument
        fields = [
            "id",
            "document_type",
            "job_id",
            "job_number",
            "created_at",
            "updated_at",
            "title",
            "company_name",
            "site_location",
            "google_doc_id",
            "google_doc_url",
        ]
        read_only_fields = [
            "id",
            "document_type",
            "job_id",
            "job_number",
            "created_at",
            "updated_at",
            "google_doc_id",
            "google_doc_url",
        ]


class SafetyDocumentListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing safety documents.
    """

    job_number = serializers.CharField(
        source="job.job_number",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = SafetyDocument
        fields = [
            "id",
            "document_type",
            "job_number",
            "created_at",
            "updated_at",
            "title",
            "site_location",
            "google_doc_url",
        ]


class SWPGenerateRequestSerializer(serializers.Serializer):
    """Request serializer for generating a new SWP (standalone)."""

    title = serializers.CharField(
        max_length=255,
        help_text="Name of the safe work procedure",
    )
    description = serializers.CharField(
        help_text="Scope and description of the procedure",
    )
    site_location = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Optional site location for the procedure",
    )


class SafetyDocumentErrorResponseSerializer(serializers.Serializer):
    """Serializer for error responses."""

    status = serializers.CharField(default="error")
    message = serializers.CharField()
