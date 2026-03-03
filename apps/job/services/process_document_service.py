"""
ProcessDocumentService - Orchestrates JSA/SWP/SOP generation workflow.

Handles:
- Generating new JSAs from job context
- Generating new SWPs (standalone)
- Generating new SOPs (standalone)
- Creating Google Docs with formatted process document content
"""

import logging

from django.db import transaction
from django.utils import timezone

from apps.job.models import Job, JobEvent, ProcessDocument
from apps.job.services.google_docs_service import GoogleDocsService
from apps.job.services.safety_ai_service import SafetyAIService
from apps.workflow.models import CompanyDefaults
from apps.workflow.services.error_persistence import persist_app_error

logger = logging.getLogger(__name__)


class ProcessDocumentService:
    """
    Service for managing process document lifecycle.

    Orchestrates JSA/SWP/SOP generation with AI content and Google Docs creation.
    """

    def __init__(self):
        """Initialize the service."""
        self.ai_service = SafetyAIService()
        self.docs_service = GoogleDocsService()

    @transaction.atomic
    def generate_jsa(self, job: Job) -> ProcessDocument:
        """
        Generate a new JSA for a job using AI and create Google Doc.

        Args:
            job: The job to generate a JSA for

        Returns:
            Created ProcessDocument with Google Doc URL
        """
        logger.info(f"Generating JSA for job {job.job_number}: {job.name}")

        try:
            # Generate JSA content using AI
            jsa_content = self.ai_service.generate_full_jsa(job=job)

            # Get company name
            company = CompanyDefaults.get_instance()
            company_name = company.company_name

            # Create Google Doc with formatted content
            doc_result = self.docs_service.create_process_document(
                document_type="jsa",
                title=jsa_content.get("title", job.name),
                content=jsa_content,
                job=job,
            )

            # Create ProcessDocument record
            jsa = ProcessDocument.objects.create(
                document_type="jsa",
                job=job,
                title=jsa_content.get("title", job.name),
                company_name=company_name,
                site_location=jsa_content.get("site_location", ""),
                google_doc_id=doc_result.document_id,
                google_doc_url=doc_result.edit_url,
            )

            # Create JobEvent for audit trail
            JobEvent.objects.create(
                job=job,
                event_type="jsa_generated",
                description=f"JSA generated: {jsa.title}",
                delta_meta={
                    "jsa_id": str(jsa.id),
                    "google_doc_url": doc_result.edit_url,
                    "generated_at": timezone.now().isoformat(),
                },
            )

            logger.info(
                f"JSA created: {jsa.id} for job {job.job_number} "
                f"-> {doc_result.edit_url}"
            )
            return jsa

        except Exception as exc:
            logger.exception(f"Failed to generate JSA for job {job.job_number}")
            persist_app_error(exc)
            raise

    @transaction.atomic
    def generate_swp(
        self,
        title: str,
        description: str,
        site_location: str = "",
        document_number: str = "",
    ) -> ProcessDocument:
        """
        Generate a new SWP (standalone) using AI and create Google Doc.

        Args:
            title: Name of the procedure
            description: Scope and description
            site_location: Optional site location
            document_number: Optional document number (e.g., '307')

        Returns:
            Created ProcessDocument with Google Doc URL
        """
        logger.info(f"Generating SWP: {title} (doc #{document_number or 'N/A'})")

        try:
            # Generate SWP content using AI
            swp_content = self.ai_service.generate_full_swp(
                title=title,
                description=description,
                site_location=site_location,
            )

            # Get company name
            company = CompanyDefaults.get_instance()
            company_name = company.company_name

            # Create Google Doc with formatted content
            doc_result = self.docs_service.create_process_document(
                document_type="swp",
                title=swp_content.get("title", title),
                content=swp_content,
                job=None,
                document_number=document_number,
            )

            # Create ProcessDocument record
            swp = ProcessDocument.objects.create(
                document_type="swp",
                job=None,  # SWPs are standalone
                document_number=document_number or None,
                title=swp_content.get("title", title),
                company_name=company_name,
                site_location=swp_content.get("site_location", site_location),
                google_doc_id=doc_result.document_id,
                google_doc_url=doc_result.edit_url,
            )

            logger.info(f"SWP created: {swp.id} -> {doc_result.edit_url}")
            return swp

        except Exception as exc:
            logger.exception(f"Failed to generate SWP: {title}")
            persist_app_error(exc)
            raise

    @transaction.atomic
    def generate_sop(
        self,
        title: str,
        description: str,
        document_number: str = "",
    ) -> ProcessDocument:
        """
        Generate a new SOP (Standard Operating Procedure) using AI and create Google Doc.

        SOPs are general procedures (not safety-specific), like "How to enter an invoice".

        Args:
            title: Name of the procedure
            description: Scope and description
            document_number: Optional document number (e.g., '307')

        Returns:
            Created ProcessDocument with Google Doc URL
        """
        logger.info(f"Generating SOP: {title} (doc #{document_number or 'N/A'})")

        try:
            # Generate SOP content using AI
            sop_content = self.ai_service.generate_full_sop(
                title=title,
                description=description,
                document_number=document_number,
            )

            # Get company name
            company = CompanyDefaults.get_instance()
            company_name = company.company_name

            # Create Google Doc with formatted content
            doc_result = self.docs_service.create_process_document(
                document_type="sop",
                title=sop_content.get("title", title),
                content=sop_content,
                job=None,
                document_number=document_number,
            )

            # Create ProcessDocument record
            sop = ProcessDocument.objects.create(
                document_type="sop",
                job=None,  # SOPs are standalone
                document_number=document_number or None,
                title=sop_content.get("title", title),
                company_name=company_name,
                site_location="",  # SOPs don't have site location
                google_doc_id=doc_result.document_id,
                google_doc_url=doc_result.edit_url,
            )

            logger.info(f"SOP created: {sop.id} -> {doc_result.edit_url}")
            return sop

        except Exception as exc:
            logger.exception(f"Failed to generate SOP: {title}")
            persist_app_error(exc)
            raise

    @transaction.atomic
    def create_blank_document(
        self,
        document_type: str,
        title: str,
        tags: list[str] | None = None,
        is_template: bool = False,
        document_number: str = "",
        site_location: str = "",
    ) -> ProcessDocument:
        """
        Create a blank ProcessDocument with a new Google Doc.

        Args:
            document_type: One of ProcessDocument.DOCUMENT_TYPES
            title: Document title
            tags: Optional list of tags
            is_template: Whether this is a template
            document_number: Optional document number
            site_location: Optional site location

        Returns:
            Created ProcessDocument with Google Doc URL
        """
        valid_types = [t[0] for t in ProcessDocument.DOCUMENT_TYPES]
        if document_type not in valid_types:
            raise ValueError(
                f"Invalid document_type '{document_type}'. "
                f"Must be one of: {valid_types}"
            )

        company = CompanyDefaults.get_instance()
        folder_id = company.gdrive_reference_library_folder_id
        if not folder_id:
            raise ValueError(
                "gdrive_reference_library_folder_id is not configured in CompanyDefaults"
            )

        doc_result = self.docs_service.create_blank_in_folder(
            title=title, folder_id=folder_id
        )

        doc = ProcessDocument.objects.create(
            document_type=document_type,
            title=title,
            tags=tags or [],
            is_template=is_template,
            document_number=document_number or None,
            company_name=company.company_name,
            site_location=site_location,
            status="draft",
            google_doc_id=doc_result.document_id,
            google_doc_url=doc_result.edit_url,
        )

        logger.info(f"Created blank document: {doc.pk} -> {doc_result.edit_url}")
        return doc

    @transaction.atomic
    def fill_template(self, template_id, job_id=None):
        """Create a new record from a template by copying the Google Doc."""
        try:
            template = ProcessDocument.objects.get(pk=template_id)
            if not template.is_template:
                raise ValueError("Document is not a template")

            # Copy Google Doc if it exists
            google_doc_id = ""
            google_doc_url = ""
            if template.google_doc_id:
                result = self.docs_service.copy_document(
                    template.google_doc_id,
                    title=f"{template.title} - {timezone.now().strftime('%Y-%m-%d')}",
                )
                google_doc_id = result.document_id
                google_doc_url = result.edit_url

            record = ProcessDocument.objects.create(
                document_type=template.document_type,
                tags=list(template.tags),  # Copy, don't share reference
                form_schema=dict(template.form_schema) if template.form_schema else {},
                title=template.title,
                document_number=template.document_number,
                company_name=template.company_name,
                site_location=template.site_location,
                google_doc_id=google_doc_id,
                google_doc_url=google_doc_url,
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
    def complete_document(self, document_id):
        """Mark a document as completed and set Google Doc to read-only."""
        try:
            doc = ProcessDocument.objects.get(pk=document_id)
            if doc.status == "completed":
                raise ValueError("Document is already completed")

            doc.status = "completed"
            doc.save(update_fields=["status", "updated_at"])

            if doc.google_doc_id:
                self.docs_service.set_readonly(doc.google_doc_id)

            logger.info("Completed document %s", doc.pk)
            return doc

        except Exception as exc:
            logger.exception("Failed to complete document %s", document_id)
            persist_app_error(exc)
            raise
