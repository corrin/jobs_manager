"""
Serializers for ProcessDocument (JSA/SWP/SOP) API endpoints.

Document content is stored in Google Docs - these serializers handle
metadata and the Google Doc reference.
"""

from rest_framework import serializers

from apps.job.models import ProcessDocument, ProcessDocumentEntry


class ProcessDocumentSerializer(serializers.ModelSerializer):
    """
    Main serializer for ProcessDocument model.

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

    parent_template_id = serializers.UUIDField(
        source="parent_template.id",
        read_only=True,
        allow_null=True,
        help_text="ID of the template this record was created from",
    )

    class Meta:
        model = ProcessDocument
        fields = [
            "id",
            "document_type",
            "document_number",
            "job_id",
            "job_number",
            "created_at",
            "updated_at",
            "title",
            "company_name",
            "site_location",
            "google_doc_id",
            "google_doc_url",
            "tags",
            "is_template",
            "status",
            "parent_template_id",
            "form_schema",
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


class ProcessDocumentListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing process documents.
    """

    job_number = serializers.CharField(
        source="job.job_number",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = ProcessDocument
        fields = [
            "id",
            "document_type",
            "document_number",
            "job_number",
            "created_at",
            "updated_at",
            "title",
            "site_location",
            "google_doc_url",
            "tags",
            "is_template",
            "status",
            "form_schema",
        ]


class ProcessDocumentEntrySerializer(serializers.ModelSerializer):
    """
    Serializer for ProcessDocumentEntry - individual entries in structured documents.
    """

    entered_by_name = serializers.CharField(
        source="entered_by.get_display_name",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = ProcessDocumentEntry
        fields = [
            "id",
            "document",
            "entry_date",
            "entered_by",
            "entered_by_name",
            "data",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "entered_by_name"]


class ProcessDocumentCreateSerializer(serializers.Serializer):
    """Request serializer for creating a blank process document."""

    document_type = serializers.ChoiceField(
        choices=ProcessDocument.DOCUMENT_TYPES,
        help_text="Document type: procedure, form, register, or reference",
    )
    title = serializers.CharField(
        max_length=255,
        help_text="Document title",
    )
    document_number = serializers.CharField(
        max_length=50,
        required=False,
        allow_blank=True,
        default="",
        help_text="Optional document number",
    )
    tags = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
        help_text="Optional list of tags",
    )
    is_template = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Whether this is a template",
    )
    site_location = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        default="",
        help_text="Optional site location",
    )


class SWPGenerateRequestSerializer(serializers.Serializer):
    """Request serializer for generating a new SWP (standalone)."""

    document_number = serializers.CharField(
        max_length=50,
        required=False,
        allow_blank=True,
        help_text="Document number (e.g., '307' for section 3, doc 7)",
    )
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


class ProcessDocumentErrorResponseSerializer(serializers.Serializer):
    """Serializer for error responses."""

    status = serializers.CharField(default="error")
    message = serializers.CharField()
