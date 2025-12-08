"""
SafetyDocument model for Job Safety Analysis (JSA) and Safe Work Procedure (SWP) documents.

JSAs are generated from jobs and use job context for AI generation, but persist as
reference documents even after jobs are archived.

SWPs are standalone documents not linked to any job, used for generic workshop procedures.
"""

import uuid

from django.db import models


class SafetyDocument(models.Model):
    """
    Unified model for JSA and SWP safety documents.

    CHECKLIST - when adding a new field, check these locations:
      1. SafetyDocumentSerializer in apps/job/serializers/safety_document_serializer.py
      2. SafetyDocument views if field affects API response
      3. SafetyPDFService if field should appear in PDF
    """

    DOCUMENT_TYPES = [
        ("jsa", "Job Safety Analysis"),
        ("swp", "Safe Work Procedure"),
    ]

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("final", "Final"),
    ]

    # Primary key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Document type
    document_type = models.CharField(
        max_length=3,
        choices=DOCUMENT_TYPES,
        help_text="Type of safety document (JSA or SWP)",
    )

    # Optional job link - required for JSA, null for SWP
    # Uses SET_NULL so JSAs persist even after job deletion
    job = models.ForeignKey(
        "Job",
        related_name="safety_documents",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Linked job (required for JSA, null for SWP)",
    )

    # Generation metadata
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="draft",
        help_text="Draft = editable, Final = PDF generated",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Document content
    title = models.CharField(
        max_length=255,
        help_text="Job name for JSA, procedure name for SWP",
    )
    company_name = models.CharField(max_length=255)
    site_location = models.CharField(
        max_length=500,
        blank=True,
        help_text="Work site location (optional for SWPs)",
    )
    description = models.TextField(
        help_text="Job description for JSA, procedure scope for SWP"
    )
    ppe_requirements = models.JSONField(
        default=list,
        help_text='List of required PPE items, e.g. ["Hard hat", "Safety glasses"]',
    )
    tasks = models.JSONField(
        default=list,
        help_text="Array of task objects with hazards and controls",
    )
    additional_notes = models.TextField(
        blank=True,
        help_text="Additional safety notes or site-specific requirements",
    )

    # Reference to generated PDF (once finalized)
    # Stored in /SafetyDocuments/ folder in Dropbox
    pdf_file_path = models.CharField(
        max_length=500,
        blank=True,
        help_text="Relative path from DROPBOX_WORKFLOW_FOLDER to generated PDF",
    )

    # Context tracking - which documents were used for AI generation
    context_document_ids = models.JSONField(
        default=list,
        help_text="UUIDs of documents used as context during generation",
    )

    class Meta:
        db_table = "workflow_safetydocument"
        ordering = ["-created_at"]
        verbose_name = "Safety Document"
        verbose_name_plural = "Safety Documents"

    def __str__(self):
        doc_type = "JSA" if self.document_type == "jsa" else "SWP"
        return f"{doc_type}: {self.title}"

    def clean(self):
        """Validate model constraints."""
        from django.core.exceptions import ValidationError

        # JSAs should have a job link (at creation time)
        # Note: We don't enforce this strictly because JSAs can outlive their jobs
        if self.document_type == "jsa" and not self.job and not self.pk:
            raise ValidationError(
                {"job": "JSA documents must be linked to a job at creation."}
            )

    @property
    def is_editable(self) -> bool:
        """Check if document can be edited (only drafts are editable)."""
        return self.status == "draft"

    @property
    def has_pdf(self) -> bool:
        """Check if document has a generated PDF."""
        return bool(self.pdf_file_path)


# Task JSON structure reference (stored in tasks JSONField):
# {
#     "step_number": 1,
#     "description": "Set up work area and exclusion zone",
#     "summary": "Area setup",  # 1-3 word summary
#     "potential_hazards": ["Pedestrian traffic", "Vehicle movements"],
#     "initial_risk_rating": "Moderate",  # Low, Moderate, High, Extreme
#     "control_measures": [
#         {"measure": "Install barrier tape", "associated_hazard": "Pedestrian traffic"},
#         {"measure": "Use spotters", "associated_hazard": "Vehicle movements"}
#     ],
#     "revised_risk_rating": "Low"
# }
