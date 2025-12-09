"""
SafetyDocument model for Job Safety Analysis (JSA) and Safe Work Procedure (SWP) documents.

JSAs are generated from jobs and use job context for AI generation, but persist as
reference documents even after jobs are archived.

SWPs are standalone documents not linked to any job, used for generic workshop procedures.

Document content is stored in Google Docs - this model stores metadata and the Doc reference.
"""

import uuid

from django.db import models


class SafetyDocument(models.Model):
    """
    Unified model for JSA and SWP safety documents.

    Document content is stored in Google Docs. This model stores:
    - Metadata (type, title, job link, dates)
    - Google Doc reference (ID and URL)
    - AI generation context tracking
    """

    DOCUMENT_TYPES = [
        ("jsa", "Job Safety Analysis"),
        ("swp", "Safe Work Procedure"),
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

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Document metadata
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
    def has_google_doc(self) -> bool:
        """Check if document has a Google Doc created."""
        return bool(self.google_doc_id)
