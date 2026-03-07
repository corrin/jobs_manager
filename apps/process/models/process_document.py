"""
ProcessDocument model for business process documents.

Covers procedures, forms, registers, and reference documents.
Documents may be linked to jobs or standalone.
Content is stored in Google Docs - this model stores metadata and the Doc reference.
"""

import uuid

from django.db import models
from simple_history.models import HistoricalRecords


class ProcessDocument(models.Model):
    """
    Unified model for business process documents.

    Document content is stored in Google Docs. This model stores:
    - Metadata (type, title, job link, dates)
    - Google Doc reference (ID and URL)
    - Classification tags and template/record workflow
    """

    DOCUMENT_TYPES = [
        ("procedure", "Procedure"),
        ("form", "Form"),
        ("register", "Register"),
        ("reference", "Reference"),
    ]

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("active", "Active"),
        ("completed", "Completed"),
        ("archived", "Archived"),
    ]

    # Primary key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Document type
    document_type = models.CharField(
        max_length=20,
        choices=DOCUMENT_TYPES,
        help_text="Document type: procedure, form, register, or reference",
    )

    # Classification
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text='Free-text tags, e.g. ["safety", "machinery", "sop"]',
    )

    # Template/record workflow
    is_template = models.BooleanField(
        default=False,
        help_text="True if this is a template that can be filled in to create records",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="active",
        help_text="Document lifecycle status",
    )
    parent_template = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="completed_records",
        help_text="Template this record was created from",
    )

    # Optional job link - required for JSA, null for SWP
    # Uses SET_NULL so JSAs persist even after job deletion
    job = models.ForeignKey(
        "job.Job",
        related_name="process_documents",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Linked job (required for JSA, null for SWP/SOP)",
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Document metadata
    document_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Document number for SWPs (e.g., '307' for section 3, doc 7)",
    )
    title = models.CharField(
        max_length=255,
        help_text="Job name for JSA, procedure name for SWP/SOP",
    )
    company_name = models.CharField(max_length=255)
    site_location = models.CharField(
        max_length=500,
        blank=True,
        help_text="Work site location (optional for SWPs)",
    )

    # Google Doc reference
    google_doc_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="Google Docs document ID",
    )
    google_doc_url = models.URLField(
        blank=True,
        help_text="URL to edit the document in Google Docs",
    )

    # Form schema for structured entry templates
    form_schema = models.JSONField(
        default=dict,
        blank=True,
        help_text="JSON schema defining entry fields for form templates",
    )

    class Meta:
        db_table = "process_document"
        ordering = ["-created_at"]
        verbose_name = "Process Document"
        verbose_name_plural = "Process Documents"

    def __str__(self):
        return f"{self.get_document_type_display()}: {self.title}"

    def clean(self):
        """Validate model constraints."""
        from django.core.exceptions import ValidationError

        # Templates cannot have a parent_template
        if self.is_template and self.parent_template:
            raise ValidationError(
                {"parent_template": "A template cannot itself have a parent template."}
            )

    history: HistoricalRecords = HistoricalRecords(
        table_name="process_historicaldocument"
    )

    @property
    def has_google_doc(self) -> bool:
        """Check if document has a Google Doc created."""
        return bool(self.google_doc_id)
