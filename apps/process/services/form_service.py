"""
FormService — manages form/register document lifecycle.

Handles:
- Creating form/register documents
- Filling templates (creating records from templates)
- Completing forms (marking as completed)
"""

import logging

from django.db import transaction

from apps.process.models import Form
from apps.process.services.google_docs_service import GoogleDocsService
from apps.workflow.models import CompanyDefaults
from apps.workflow.services.error_persistence import persist_app_error

logger = logging.getLogger(__name__)


class FormService:
    """Service for managing form/register lifecycle."""

    def __init__(self):
        self.docs_service = GoogleDocsService()

    @transaction.atomic
    def create_form(
        self,
        title: str,
        document_type: str = "form",
        tags: list[str] | None = None,
        is_template: bool = False,
        document_number: str = "",
        form_schema: dict | None = None,
    ) -> Form:
        """Create a form/register document (no Google Doc)."""
        if document_type not in ("form", "register"):
            raise ValueError(
                f"create_form only accepts 'form' or 'register', "
                f"got '{document_type}'"
            )

        company = CompanyDefaults.get_instance()

        doc = Form.objects.create(
            document_type=document_type,
            title=title,
            tags=tags or [],
            is_template=is_template,
            document_number=document_number or None,
            company_name=company.company_name,
            form_schema=form_schema or {},
            status="active" if is_template else "draft",
        )

        logger.info(f"Created form: {doc.pk} (type={document_type})")
        return doc

    @transaction.atomic
    def fill_template(self, template_id, job_id=None):
        """Create a new record from a template."""
        try:
            template = Form.objects.get(pk=template_id)
            if not template.is_template:
                raise ValueError("Document is not a template")

            record = Form.objects.create(
                document_type=template.document_type,
                tags=list(template.tags),
                form_schema=dict(template.form_schema) if template.form_schema else {},
                title=template.title,
                document_number=template.document_number,
                company_name=template.company_name,
                is_template=False,
                status="draft",
                parent_template=template,
                job_id=job_id,
            )
            logger.info("Created record %s from template %s", record.pk, template.pk)
            return record

        except Exception as exc:
            logger.exception("Failed to fill template %s", template_id)
            persist_app_error(exc)
            raise

    @transaction.atomic
    def complete_form(self, form_id):
        """Mark a form as completed."""
        try:
            form = Form.objects.get(pk=form_id)
            if form.status == "completed":
                raise ValueError("Document is already completed")

            form.status = "completed"
            form.save(update_fields=["status", "updated_at"])

            logger.info("Completed form %s", form.pk)
            return form

        except Exception as exc:
            logger.exception("Failed to complete form %s", form_id)
            persist_app_error(exc)
            raise
