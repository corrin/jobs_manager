"""
Chat File Service

Handles extraction of file attachments from chat messages and conversion
to formats suitable for AI model consumption.

Note: Multimodal file handling varies by LLM provider. This service provides
basic file metadata and content extraction. For actual multimodal input,
use the LLMService.create_image_message() or create_pdf_message() helpers.
"""

import base64
import logging
import os
from typing import Any, Dict, List, Set

from apps.job.models import JobFile, JobQuoteChat

logger = logging.getLogger(__name__)


class ChatFileService:
    """Service for extracting and processing files attached to chat messages."""

    @staticmethod
    def extract_file_ids_from_chat_history(
        chat_messages: List[JobQuoteChat],
    ) -> Set[str]:
        """
        Extract all file IDs from chat message metadata.

        Args:
            chat_messages: List of JobQuoteChat messages

        Returns:
            Set of file UUIDs referenced in the chat
        """
        file_ids = set()

        for message in chat_messages:
            if message.metadata and "file_ids" in message.metadata:
                file_ids.update(message.metadata["file_ids"])

        logger.debug(f"Extracted {len(file_ids)} file IDs from chat history")
        return file_ids

    @staticmethod
    def fetch_job_files(job_id: str, file_ids: Set[str]) -> List[JobFile]:
        """
        Fetch JobFile records for the given file IDs.

        Args:
            job_id: UUID of the job
            file_ids: Set of file UUIDs to fetch

        Returns:
            List of active JobFile instances
        """
        if not file_ids:
            return []

        files = JobFile.objects.filter(
            job_id=job_id, id__in=file_ids, status="active"
        ).select_related("job")

        logger.debug(f"Fetched {files.count()} active files for job {job_id}")
        return list(files)

    @staticmethod
    def get_file_info(job_file: JobFile) -> Dict[str, Any]:
        """
        Get file information for a JobFile.

        Args:
            job_file: JobFile instance

        Returns:
            Dict with file metadata
        """
        file_full_path = os.path.join(job_file.full_path, job_file.filename)

        return {
            "id": str(job_file.id),
            "filename": job_file.filename,
            "mime_type": job_file.mime_type or "application/octet-stream",
            "full_path": file_full_path,
            "exists": os.path.exists(file_full_path),
        }

    @staticmethod
    def get_file_as_base64(job_file: JobFile) -> Dict[str, Any]:
        """
        Get file content as base64 for multimodal API calls.

        Args:
            job_file: JobFile instance

        Returns:
            Dict with base64 content and metadata, or error info
        """
        file_full_path = os.path.join(job_file.full_path, job_file.filename)
        mime_type = job_file.mime_type or "application/octet-stream"

        if not os.path.exists(file_full_path):
            logger.warning(
                f"File not found: {file_full_path} for JobFile {job_file.id}"
            )
            return {
                "error": True,
                "message": f"File not found: {job_file.filename}",
            }

        # Check if file type is supported for multimodal
        supported_types = [
            "image/",
            "application/pdf",
        ]

        if not any(mime_type.startswith(t) for t in supported_types):
            return {
                "error": False,
                "text_only": True,
                "filename": job_file.filename,
                "mime_type": mime_type,
            }

        try:
            with open(file_full_path, "rb") as f:
                content = base64.b64encode(f.read()).decode("utf-8")

            return {
                "error": False,
                "filename": job_file.filename,
                "mime_type": mime_type,
                "base64_content": content,
                "data_url": f"data:{mime_type};base64,{content}",
            }
        except Exception as e:
            logger.error(f"Error reading file {file_full_path}: {e}")
            return {
                "error": True,
                "message": f"Error reading file: {job_file.filename}",
            }

    @staticmethod
    def build_file_reference(job_file: JobFile) -> str:
        """
        Build a text reference for a file (for non-multimodal contexts).

        Args:
            job_file: JobFile instance

        Returns:
            Text description of the file attachment
        """
        mime_type = job_file.mime_type or "unknown type"
        return f"[Attached file: {job_file.filename} ({mime_type})]"

    @staticmethod
    def build_file_references(job_files: List[JobFile]) -> str:
        """
        Build text references for multiple files.

        Args:
            job_files: List of JobFile instances

        Returns:
            Text description of file attachments
        """
        if not job_files:
            return ""

        refs = [ChatFileService.build_file_reference(f) for f in job_files]
        return "\n".join(refs)
