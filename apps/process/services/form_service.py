"""
FormService — manages form/register document lifecycle.

Handles:
- Creating form/register definitions
- Creating entries (filled-in instances of forms)
"""

import logging
from datetime import date

from django.db import transaction

from apps.process.models import Form, FormEntry
from apps.workflow.services.error_persistence import persist_app_error

logger = logging.getLogger(__name__)


class FormService:
    """Service for managing form/register lifecycle."""

    @transaction.atomic
    def create_form(
        self,
        title: str,
        document_type: str = "form",
        tags: list[str] | None = None,
        document_number: str = "",
        form_schema: dict | None = None,
    ) -> Form:
        """Create a form/register definition."""
        if document_type not in ("form", "register"):
            raise ValueError(
                f"create_form only accepts 'form' or 'register', "
                f"got '{document_type}'"
            )

        doc = Form.objects.create(
            document_type=document_type,
            title=title,
            tags=tags or [],
            document_number=document_number or None,
            form_schema=form_schema or {},
            status="active",
        )

        logger.info(f"Created form: {doc.pk} (type={document_type})")
        return doc

    @transaction.atomic
    def create_entry(
        self,
        form_id,
        job_id=None,
        entered_by=None,
        entry_date=None,
        data=None,
    ) -> FormEntry:
        """Create a new FormEntry linked to a Form definition."""
        try:
            form = Form.objects.get(pk=form_id)

            entry = FormEntry.objects.create(
                form=form,
                job_id=job_id,
                entered_by=entered_by,
                entry_date=entry_date or date.today(),
                data=data or {},
            )
            logger.info("Created entry %s for form %s", entry.pk, form.pk)
            return entry

        except Exception as exc:
            logger.exception("Failed to create entry for form %s", form_id)
            persist_app_error(exc)
            raise
