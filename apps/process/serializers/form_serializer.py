"""
Serializers for Form and FormEntry API endpoints.

Forms are structured entry documents (checklists, registers, logs).
No Google Doc — data is stored as FormEntry rows.
"""

from rest_framework import serializers

from apps.process.models import Form, FormEntry


class FormEntrySerializer(serializers.ModelSerializer):
    """Serializer for FormEntry — individual entries in structured forms."""

    entered_by_name = serializers.CharField(
        source="entered_by.get_display_name",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = FormEntry
        fields = [
            "id",
            "form",
            "entry_date",
            "entered_by",
            "entered_by_name",
            "data",
            "created_at",
        ]
        read_only_fields = ["id", "form", "entered_by", "created_at"]


class FormListSerializer(serializers.ModelSerializer):
    """List serializer for form endpoints — includes form_schema."""

    class Meta:
        model = Form
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
    """Detail serializer for forms — adds job_id, job_number, parent_template_id."""

    job_id = serializers.UUIDField(source="job.id", read_only=True, allow_null=True)
    job_number = serializers.CharField(
        source="job.job_number", read_only=True, allow_null=True
    )
    parent_template_id = serializers.UUIDField(
        source="parent_template.id", read_only=True, allow_null=True
    )

    class Meta:
        model = Form
        fields = [
            "id",
            "document_type",
            "document_number",
            "title",
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
        model = Form
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
