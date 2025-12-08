"""
Serializers for SafetyDocument (JSA/SWP) API endpoints.
"""

from rest_framework import serializers

from apps.job.models import SafetyDocument


class ControlMeasureSerializer(serializers.Serializer):
    """Serializer for individual control measures within a task."""

    measure = serializers.CharField(help_text="The control measure description")
    associated_hazard = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="The hazard this control addresses",
    )


class SafetyTaskSerializer(serializers.Serializer):
    """Serializer for individual tasks within a safety document."""

    step_number = serializers.IntegerField(min_value=1)
    description = serializers.CharField()
    summary = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="1-3 word summary of the task",
    )
    potential_hazards = serializers.ListField(
        child=serializers.CharField(),
        help_text="List of potential hazards for this task",
    )
    initial_risk_rating = serializers.ChoiceField(
        choices=["Low", "Moderate", "High", "Extreme"],
        help_text="Risk rating before controls are applied",
    )
    control_measures = ControlMeasureSerializer(
        many=True,
        help_text="List of control measures to mitigate hazards",
    )
    revised_risk_rating = serializers.ChoiceField(
        choices=["Low", "Moderate", "High", "Extreme"],
        help_text="Risk rating after controls are applied",
    )


class SafetyDocumentSerializer(serializers.ModelSerializer):
    """
    Main serializer for SafetyDocument model.

    Used for CRUD operations on existing documents.
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
    tasks = SafetyTaskSerializer(many=True)
    pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = SafetyDocument
        fields = [
            "id",
            "document_type",
            "job_id",
            "job_number",
            "status",
            "created_at",
            "updated_at",
            "title",
            "company_name",
            "site_location",
            "description",
            "ppe_requirements",
            "tasks",
            "additional_notes",
            "pdf_file_path",
            "pdf_url",
            "context_document_ids",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "pdf_file_path",
            "context_document_ids",
        ]

    def get_pdf_url(self, obj: SafetyDocument) -> str | None:
        """Generate URL for PDF download if available."""
        if not obj.pdf_file_path:
            return None
        request = self.context.get("request")
        if not request:
            return None
        # URL will be: /api/rest/safety-documents/{id}/pdf/
        return request.build_absolute_uri(f"/api/rest/safety-documents/{obj.id}/pdf/")

    def validate(self, data):
        """Validate document data."""
        # Only drafts can be edited
        if self.instance and self.instance.status == "final":
            raise serializers.ValidationError(
                "Cannot edit a finalized document. Create a new version instead."
            )
        return data

    def validate_tasks(self, tasks):
        """Validate tasks structure."""
        if not tasks:
            raise serializers.ValidationError("At least one task is required.")

        # Validate step numbers are sequential
        step_numbers = [task.get("step_number") for task in tasks]
        expected = list(range(1, len(tasks) + 1))
        if sorted(step_numbers) != expected:
            raise serializers.ValidationError(
                "Task step numbers must be sequential starting from 1."
            )

        return tasks


class SafetyDocumentListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing safety documents.

    Excludes full task details for performance.
    """

    job_number = serializers.CharField(
        source="job.job_number",
        read_only=True,
        allow_null=True,
    )
    task_count = serializers.SerializerMethodField()

    class Meta:
        model = SafetyDocument
        fields = [
            "id",
            "document_type",
            "job_number",
            "status",
            "created_at",
            "updated_at",
            "title",
            "site_location",
            "task_count",
            "has_pdf",
        ]

    def get_task_count(self, obj: SafetyDocument) -> int:
        """Get number of tasks in the document."""
        return len(obj.tasks) if obj.tasks else 0


class JSAGenerateRequestSerializer(serializers.Serializer):
    """Request serializer for generating a new JSA from a job."""

    # No additional parameters needed - job context is provided via URL


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


class TaskHazardsGenerateRequestSerializer(serializers.Serializer):
    """Request serializer for generating hazards for a specific task."""

    task_description = serializers.CharField(
        help_text="Description of the task to generate hazards for",
    )


class TaskControlsGenerateRequestSerializer(serializers.Serializer):
    """Request serializer for generating controls for hazards."""

    hazards = serializers.ListField(
        child=serializers.CharField(),
        help_text="List of hazards to generate controls for",
    )


class TaskHazardsResponseSerializer(serializers.Serializer):
    """Response serializer for generated hazards."""

    hazards = serializers.ListField(
        child=serializers.CharField(),
        help_text="List of generated hazards",
    )


class TaskControlsResponseSerializer(serializers.Serializer):
    """Response serializer for generated controls."""

    controls = ControlMeasureSerializer(
        many=True,
        help_text="List of generated control measures",
    )


class SafetyDocumentFinalizeResponseSerializer(serializers.Serializer):
    """Response serializer for document finalization."""

    id = serializers.UUIDField()
    status = serializers.CharField()
    pdf_file_path = serializers.CharField()
    pdf_url = serializers.URLField()
    message = serializers.CharField()


class SafetyDocumentErrorResponseSerializer(serializers.Serializer):
    """Serializer for error responses."""

    status = serializers.CharField(default="error")
    message = serializers.CharField()
