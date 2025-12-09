"""
SafetyDocumentService - Orchestrates JSA/SWP generation workflow.

Handles:
- Generating new JSAs from job context
- Generating new SWPs (standalone)
- Creating Google Docs with formatted safety content
"""

import logging

from django.db import transaction
from django.utils import timezone

from apps.job.models import Job, JobEvent, SafetyDocument
from apps.job.services.google_docs_service import GoogleDocsService
from apps.job.services.safety_ai_service import SafetyAIService
from apps.workflow.models import CompanyDefaults
from apps.workflow.services.error_persistence import persist_app_error

logger = logging.getLogger(__name__)


class SafetyDocumentService:
    """
    Service for managing safety document lifecycle.

    Orchestrates JSA/SWP generation with AI content and Google Docs creation.
    """

    def __init__(self):
        """Initialize the service."""
        self.ai_service = SafetyAIService()
        self.docs_service = GoogleDocsService()

    @transaction.atomic
    def generate_jsa(self, job: Job) -> SafetyDocument:
        """
        Generate a new JSA for a job using AI and create Google Doc.

        Args:
            job: The job to generate a JSA for

        Returns:
            Created SafetyDocument with Google Doc URL
        """
        logger.info(f"Generating JSA for job {job.job_number}: {job.name}")

        try:
            # Generate JSA content using AI
            jsa_content = self.ai_service.generate_full_jsa(job=job)

            # Get company name
            company = CompanyDefaults.objects.first()
            company_name = company.company_name if company else "Morris Sheetmetal"

            # Create Google Doc with formatted content
            doc_result = self.docs_service.create_safety_document(
                document_type="jsa",
                title=jsa_content.get("title", job.name),
                content=jsa_content,
                job=job,
            )

            # Create SafetyDocument record
            jsa = SafetyDocument.objects.create(
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
    ) -> SafetyDocument:
        """
        Generate a new SWP (standalone) using AI and create Google Doc.

        Args:
            title: Name of the procedure
            description: Scope and description
            site_location: Optional site location
            document_number: Optional document number (e.g., '307')

        Returns:
            Created SafetyDocument with Google Doc URL
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
            company = CompanyDefaults.objects.first()
            company_name = company.company_name if company else "Morris Sheetmetal"

            # Create Google Doc with formatted content
            doc_result = self.docs_service.create_safety_document(
                document_type="swp",
                title=swp_content.get("title", title),
                content=swp_content,
                job=None,
                document_number=document_number,
            )

            # Create SafetyDocument record
            swp = SafetyDocument.objects.create(
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
    ) -> SafetyDocument:
        """
        Generate a new SOP (Standard Operating Procedure) using AI and create Google Doc.

        SOPs are general procedures (not safety-specific), like "How to enter an invoice".

        Args:
            title: Name of the procedure
            description: Scope and description
            document_number: Optional document number (e.g., '307')

        Returns:
            Created SafetyDocument with Google Doc URL
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
            company = CompanyDefaults.objects.first()
            company_name = company.company_name if company else "Morris Sheetmetal"

            # Create Google Doc with formatted content
            doc_result = self.docs_service.create_safety_document(
                document_type="sop",
                title=sop_content.get("title", title),
                content=sop_content,
                job=None,
                document_number=document_number,
            )

            # Create SafetyDocument record
            sop = SafetyDocument.objects.create(
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
