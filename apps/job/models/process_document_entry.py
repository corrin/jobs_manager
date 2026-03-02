"""
ProcessDocumentEntry - generic line entries for structured forms and registers.

Used for documents where content is structured data (inspections, logs, checklists)
rather than prose (which lives in Google Docs).
"""

import uuid

from django.db import models


class ProcessDocumentEntry(models.Model):
    """
    A single entry/line in a structured process document.

    The `data` JSON field schema varies by document type. Each form type
    defines its own expected fields.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    document = models.ForeignKey(
        "ProcessDocument",
        related_name="entries",
        on_delete=models.CASCADE,
        help_text="Parent process document",
    )

    entry_date = models.DateField(
        help_text="Date this entry relates to",
    )

    entered_by = models.ForeignKey(
        "accounts.Staff",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Staff member who created this entry",
    )

    data = models.JSONField(
        default=dict,
        help_text="Entry data - schema varies by document type",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workflow_processdocumententry"
        ordering = ["-entry_date", "-created_at"]
        verbose_name = "Process Document Entry"
        verbose_name_plural = "Process Document Entries"

    def __str__(self):
        return f"Entry {self.entry_date} on {self.document.title}"
