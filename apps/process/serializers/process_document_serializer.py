"""
Serializers for ProcessDocument (JSA/SWP/SOP) API endpoints.

Document content is stored in Google Docs - these serializers handle
metadata and the Google Doc reference.
"""

from rest_framework import serializers

from apps.process.models import ProcessDocument, ProcessDocumentEntry


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
        read_only_fields = ["id", "document", "entered_by", "created_at"]


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


class ProcedureListSerializer(serializers.ModelSerializer):
    """List serializer for procedure endpoints — includes google_doc_url, excludes form_schema."""

    job_number = serializers.CharField(
        source="job.job_number", read_only=True, allow_null=True
    )

    class Meta:
        model = ProcessDocument
        fields = [
            "id",
            "document_type",
            "document_number",
            "title",
            "site_location",
            "google_doc_url",
            "job_number",
            "tags",
            "is_template",
            "status",
            "created_at",
            "updated_at",
        ]


class ProcedureDetailSerializer(serializers.ModelSerializer):
    """Detail serializer for procedures — adds google_doc_id, company_name, job_id, parent_template_id."""

    job_id = serializers.UUIDField(source="job.id", read_only=True, allow_null=True)
    job_number = serializers.CharField(
        source="job.job_number", read_only=True, allow_null=True
    )
    parent_template_id = serializers.UUIDField(
        source="parent_template.id", read_only=True, allow_null=True
    )

    class Meta:
        model = ProcessDocument
        fields = [
            "id",
            "document_type",
            "document_number",
            "title",
            "company_name",
            "site_location",
            "google_doc_id",
            "google_doc_url",
            "job_id",
            "job_number",
            "tags",
            "is_template",
            "status",
            "parent_template_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "document_type",
            "created_at",
            "updated_at",
            "google_doc_id",
            "google_doc_url",
        ]


class ProcedureCreateSerializer(serializers.Serializer):
    """Request serializer for creating a blank procedure."""

    title = serializers.CharField(max_length=255)
    document_number = serializers.CharField(
        max_length=50, required=False, allow_blank=True, default=""
    )
    tags = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    site_location = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )
    is_template = serializers.BooleanField(required=False, default=False)


class ProcedureUpdateSerializer(serializers.ModelSerializer):
    """Update serializer for procedures."""

    class Meta:
        model = ProcessDocument
        fields = [
            "title",
            "document_number",
            "tags",
            "site_location",
            "status",
            "is_template",
        ]
        extra_kwargs = {
            "title": {"required": False},
            "document_number": {"required": False},
            "tags": {"required": False},
            "site_location": {"required": False},
            "status": {"required": False},
            "is_template": {"required": False},
        }


class FormListSerializer(serializers.ModelSerializer):
    """List serializer for form endpoints — includes form_schema, excludes google_doc_url/google_doc_id."""

    class Meta:
        model = ProcessDocument
        fields = [
            "id",
            "document_type",
            "document_number",
            "title",
            "tags",
            "is_template",
            "status",
            "form_schema",
            "created_at",
            "updated_at",
        ]


class FormDetailSerializer(serializers.ModelSerializer):
    """Detail serializer for forms — adds company_name, site_location, job_id, job_number, parent_template_id."""

    job_id = serializers.UUIDField(source="job.id", read_only=True, allow_null=True)
    job_number = serializers.CharField(
        source="job.job_number", read_only=True, allow_null=True
    )
    parent_template_id = serializers.UUIDField(
        source="parent_template.id", read_only=True, allow_null=True
    )

    class Meta:
        model = ProcessDocument
        fields = [
            "id",
            "document_type",
            "document_number",
            "title",
            "company_name",
            "site_location",
            "tags",
            "is_template",
            "status",
            "form_schema",
            "parent_template_id",
            "job_id",
            "job_number",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "document_type",
            "created_at",
            "updated_at",
        ]


class FormCreateSerializer(serializers.Serializer):
    """Request serializer for creating a form document (no Google Doc)."""

    title = serializers.CharField(max_length=255)
    document_number = serializers.CharField(
        max_length=50, required=False, allow_blank=True, default=""
    )
    tags = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    form_schema = serializers.JSONField(required=False, default=dict)
    is_template = serializers.BooleanField(required=False, default=False)


class FormUpdateSerializer(serializers.ModelSerializer):
    """Update serializer for forms."""

    class Meta:
        model = ProcessDocument
        fields = [
            "title",
            "document_number",
            "tags",
            "form_schema",
            "status",
            "is_template",
        ]
        extra_kwargs = {
            "title": {"required": False},
            "document_number": {"required": False},
            "tags": {"required": False},
            "form_schema": {"required": False},
            "status": {"required": False},
            "is_template": {"required": False},
        }


class ProcessDocumentErrorResponseSerializer(serializers.Serializer):
    """Serializer for error responses."""

    status = serializers.CharField(default="error")
    message = serializers.CharField()
