"""
Form model — structured entry documents (forms, registers).

Forms are append-only logs. Registers allow editing entries.
Both use FormEntry for structured data rows.
"""

import uuid

from django.db import models
from simple_history.models import HistoricalRecords


class Form(models.Model):
    """
    A structured entry document (form or register).

    No Google Doc — data is stored as FormEntry rows.
    Templates define the schema; records are filled instances.
    """

    DOCUMENT_TYPES = [
        ("form", "Form"),
        ("register", "Register"),
    ]

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("active", "Active"),
        ("completed", "Completed"),
        ("archived", "Archived"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    document_type = models.CharField(
        max_length=20,
        choices=DOCUMENT_TYPES,
        help_text="Document type: form or register",
    )

    title = models.CharField(max_length=255)
    document_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
    )
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text='Free-text tags, e.g. ["safety", "inspection"]',
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="active",
    )

    is_template = models.BooleanField(
        default=False,
        help_text="True if this is a template that can be filled in to create records",
    )
    parent_template = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="completed_records",
        help_text="Template this record was created from",
    )

    job = models.ForeignKey(
        "job.Job",
        related_name="forms",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Linked job (e.g. incident forms)",
    )

    form_schema = models.JSONField(
        default=dict,
        blank=True,
        help_text="JSON schema defining entry fields for form templates",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history: HistoricalRecords = HistoricalRecords(table_name="process_historicalform")

    class Meta:
        db_table = "process_form"
        ordering = ["-created_at"]
        verbose_name = "Form"
        verbose_name_plural = "Forms"

    def __str__(self):
        return f"{self.get_document_type_display()}: {self.title}"

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.is_template and self.parent_template:
            raise ValidationError(
                {"parent_template": "A template cannot itself have a parent template."}
            )
