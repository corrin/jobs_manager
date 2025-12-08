"""
SafetyDocumentService - Orchestrates JSA/SWP generation workflow.

Handles:
- Generating new JSAs from job context
- Generating new SWPs (standalone)
- Finding similar historical documents for context injection
- Coordinating between AI service and persistence
- Finalizing documents (generating PDF)
"""

import logging
import os
from io import BytesIO

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.job.models import Job, JobEvent, SafetyDocument
from apps.job.services.safety_ai_service import DEFAULT_PPE, SafetyAIService
from apps.workflow.models import CompanyDefaults
from apps.workflow.services.error_persistence import persist_app_error

logger = logging.getLogger(__name__)


class SafetyDocumentService:
    """
    Service for managing safety document lifecycle.

    Orchestrates JSA/SWP generation, similarity matching, and finalization.
    """

    def __init__(self):
        """Initialize the service with AI service."""
        self.ai_service = SafetyAIService()

    def find_similar_documents(
        self,
        description: str,
        doc_type: str | None = None,
        limit: int = 3,
        exclude_id: str | None = None,
    ) -> list[SafetyDocument]:
        """
        Find similar safety documents based on description.

        Uses keyword matching for Phase 1 implementation.
        Future: Could use AI embeddings for semantic similarity.

        Args:
            description: Text to match against
            doc_type: Optional filter for 'jsa' or 'swp'
            limit: Maximum number of documents to return
            exclude_id: Optional document ID to exclude from results

        Returns:
            List of similar SafetyDocument objects
        """
        if not description:
            return []

        # Extract keywords (simple word tokenization)
        words = description.lower().split()
        # Filter common words and short words
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "from",
            "as",
            "is",
            "was",
            "are",
            "were",
            "been",
            "be",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "must",
            "shall",
            "can",
            "need",
            "this",
            "that",
            "these",
            "those",
        }
        keywords = [w for w in words if len(w) > 3 and w not in stop_words]

        if not keywords:
            return []

        # Build query for keyword matching
        query = Q()
        for keyword in keywords[:10]:  # Limit to first 10 keywords
            query |= Q(title__icontains=keyword)
            query |= Q(description__icontains=keyword)

        queryset = SafetyDocument.objects.filter(query)

        # Apply doc_type filter if specified
        if doc_type:
            queryset = queryset.filter(document_type=doc_type)

        # Exclude specific document if specified
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)

        # Prefer finalized documents (they've been reviewed)
        queryset = queryset.order_by("-status", "-created_at")

        return list(queryset[:limit])

    @transaction.atomic
    def generate_jsa(self, job: Job) -> SafetyDocument:
        """
        Generate a new draft JSA for a job using AI.

        Args:
            job: The job to generate a JSA for

        Returns:
            Created SafetyDocument (draft status)
        """
        logger.info(f"Generating JSA for job {job.job_number}: {job.name}")

        try:
            # Find similar JSAs for context
            description = f"{job.name} {job.description or ''}"
            similar_docs = self.find_similar_documents(
                description=description,
                doc_type="jsa",
                limit=3,
            )
            logger.debug(f"Found {len(similar_docs)} similar JSAs for context")

            # Generate JSA content using AI
            jsa_content = self.ai_service.generate_full_jsa(
                job=job,
                context_docs=similar_docs,
            )

            # Get company name
            company = CompanyDefaults.objects.first()
            company_name = company.company_name if company else "Morris Sheetmetal"

            # Create SafetyDocument
            jsa = SafetyDocument.objects.create(
                document_type="jsa",
                job=job,
                status="draft",
                title=jsa_content.get("title", job.name),
                company_name=company_name,
                site_location=jsa_content.get("site_location", ""),
                description=jsa_content.get("description", job.description or ""),
                ppe_requirements=jsa_content.get(
                    "ppe_requirements", DEFAULT_PPE.copy()
                ),
                tasks=jsa_content.get("tasks", []),
                additional_notes=jsa_content.get("additional_notes", ""),
                context_document_ids=[str(doc.id) for doc in similar_docs],
            )

            # Create JobEvent for audit trail
            JobEvent.objects.create(
                job=job,
                event_type="jsa_generated",
                description=f"JSA generated: {jsa.title}",
                delta_meta={
                    "jsa_id": str(jsa.id),
                    "generated_at": timezone.now().isoformat(),
                    "context_document_count": len(similar_docs),
                    "task_count": len(jsa.tasks),
                },
            )

            logger.info(f"JSA created: {jsa.id} for job {job.job_number}")
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
    ) -> SafetyDocument:
        """
        Generate a new draft SWP (standalone) using AI.

        Args:
            title: Name of the procedure
            description: Scope and description
            site_location: Optional site location

        Returns:
            Created SafetyDocument (draft status)
        """
        logger.info(f"Generating SWP: {title}")

        try:
            # Find similar documents for context
            similar_docs = self.find_similar_documents(
                description=f"{title} {description}",
                limit=3,
            )
            logger.debug(f"Found {len(similar_docs)} similar documents for context")

            # Generate SWP content using AI
            swp_content = self.ai_service.generate_full_swp(
                title=title,
                description=description,
                site_location=site_location,
                context_docs=similar_docs,
            )

            # Get company name
            company = CompanyDefaults.objects.first()
            company_name = company.company_name if company else "Morris Sheetmetal"

            # Create SafetyDocument
            swp = SafetyDocument.objects.create(
                document_type="swp",
                job=None,  # SWPs are standalone
                status="draft",
                title=swp_content.get("title", title),
                company_name=company_name,
                site_location=swp_content.get("site_location", site_location),
                description=swp_content.get("description", description),
                ppe_requirements=swp_content.get(
                    "ppe_requirements", DEFAULT_PPE.copy()
                ),
                tasks=swp_content.get("tasks", []),
                additional_notes=swp_content.get("additional_notes", ""),
                context_document_ids=[str(doc.id) for doc in similar_docs],
            )

            logger.info(f"SWP created: {swp.id}")
            return swp

        except Exception as exc:
            logger.exception(f"Failed to generate SWP: {title}")
            persist_app_error(exc)
            raise

    @transaction.atomic
    def finalize_document(self, document: SafetyDocument) -> tuple[BytesIO, str]:
        """
        Finalize a safety document by generating PDF and saving to Dropbox.

        Args:
            document: The SafetyDocument to finalize

        Returns:
            Tuple of (PDF buffer, relative file path)
        """
        if document.status == "final":
            raise ValueError("Document is already finalized")

        logger.info(f"Finalizing safety document: {document.id}")

        try:
            # Import PDF service here to avoid circular imports
            from apps.job.services.safety_pdf_service import SafetyPDFService

            pdf_service = SafetyPDFService()

            # Generate PDF
            pdf_buffer = pdf_service.create_pdf(document)

            # Read content for saving
            pdf_content = pdf_buffer.read()
            pdf_buffer.seek(0)

            # Generate filename
            timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
            doc_type = document.document_type.upper()
            safe_title = "".join(
                c for c in document.title if c.isalnum() or c in " -_"
            ).strip()[:50]
            filename = f"{doc_type}_{safe_title}_{timestamp}.pdf"

            # Define storage folder (dedicated SafetyDocuments folder)
            safety_folder = os.path.join(
                settings.DROPBOX_WORKFLOW_FOLDER, "SafetyDocuments"
            )
            os.makedirs(safety_folder, exist_ok=True)

            # Save PDF to disk
            file_path = os.path.join(safety_folder, filename)
            with open(file_path, "wb") as f:
                f.write(pdf_content)
            os.chmod(file_path, 0o664)

            # Create relative path for database
            relative_path = os.path.relpath(file_path, settings.DROPBOX_WORKFLOW_FOLDER)

            # Update document
            document.status = "final"
            document.pdf_file_path = relative_path
            document.save()

            # Create JobEvent if linked to a job
            if document.job:
                JobEvent.objects.create(
                    job=document.job,
                    event_type="jsa_finalized",
                    description=f"{doc_type} finalized: {document.title}",
                    delta_meta={
                        "document_id": str(document.id),
                        "filename": filename,
                        "finalized_at": timezone.now().isoformat(),
                    },
                )

            logger.info(f"Safety document finalized: {document.id} -> {relative_path}")
            return pdf_buffer, relative_path

        except Exception as exc:
            logger.exception(f"Failed to finalize safety document: {document.id}")
            persist_app_error(exc)
            raise

    def update_task_hazards(
        self, document: SafetyDocument, task_index: int
    ) -> list[str]:
        """
        Generate hazards for a specific task using AI.

        Args:
            document: The safety document
            task_index: Index of the task (0-based)

        Returns:
            List of generated hazards
        """
        if document.status == "final":
            raise ValueError("Cannot modify finalized document")

        if task_index < 0 or task_index >= len(document.tasks):
            raise ValueError(f"Invalid task index: {task_index}")

        task = document.tasks[task_index]
        task_description = task.get("description", "")

        # Generate hazards using AI
        hazards = self.ai_service.generate_hazards(task_description)

        # Update task
        document.tasks[task_index]["potential_hazards"] = hazards
        document.save()

        return hazards

    def update_task_controls(
        self, document: SafetyDocument, task_index: int
    ) -> list[dict[str, str]]:
        """
        Generate controls for a specific task's hazards using AI.

        Args:
            document: The safety document
            task_index: Index of the task (0-based)

        Returns:
            List of generated control measures
        """
        if document.status == "final":
            raise ValueError("Cannot modify finalized document")

        if task_index < 0 or task_index >= len(document.tasks):
            raise ValueError(f"Invalid task index: {task_index}")

        task = document.tasks[task_index]
        hazards = task.get("potential_hazards", [])

        if not hazards:
            raise ValueError("Task has no hazards to generate controls for")

        # Generate controls using AI
        controls = self.ai_service.generate_controls(hazards)

        # Update task
        document.tasks[task_index]["control_measures"] = controls
        document.save()

        return controls
