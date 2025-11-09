"""
Chat File Service

Handles extraction of file attachments from chat messages and conversion
to formats suitable for AI model consumption (Gemini).
"""

import logging
import os
from typing import Any, List, Set

import google.generativeai as genai

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
    def build_file_content_for_gemini(job_file: JobFile) -> Any:
        """
        Convert a JobFile into content suitable for Gemini API.

        Gemini supports uploading files via genai.upload_file() for:
        - Images (JPEG, PNG, GIF, WebP)
        - PDFs
        - Audio, Video, and other supported formats

        Args:
            job_file: JobFile instance to process

        Returns:
            Gemini File object or dict with text for unsupported files
        """
        mime_type = job_file.mime_type or "application/octet-stream"
        file_full_path = os.path.join(job_file.full_path, job_file.filename)

        # Check if file exists
        if not os.path.exists(file_full_path):
            logger.warning(
                f"File not found: {file_full_path} for JobFile {job_file.id}"
            )
            return {"text": f"[File not found: {job_file.filename}]"}

        # Upload supported file types using Gemini File API
        supported_types = [
            "image/",
            "application/pdf",
            "audio/",
            "video/",
        ]

        if any(mime_type.startswith(t) for t in supported_types):
            return ChatFileService._upload_file_to_gemini(
                file_full_path, mime_type, job_file.filename
            )

        # Handle other files
        return {"text": f"\n\n[File attached: {job_file.filename} - {mime_type}]\n"}

    @staticmethod
    def _upload_file_to_gemini(file_path: str, mime_type: str, filename: str) -> Any:
        """
        Upload a file to Gemini using the File API.

        Args:
            file_path: Full path to the file
            mime_type: MIME type of the file
            filename: Display name for the file

        Returns:
            Gemini File object or error dict
        """
        try:
            # Upload file to Gemini
            uploaded_file = genai.upload_file(
                path=file_path, mime_type=mime_type, display_name=filename
            )

            logger.info(
                f"Uploaded file to Gemini: {filename} (URI: {uploaded_file.uri})"
            )
            return uploaded_file

        except Exception as e:
            logger.error(f"Failed to upload file {file_path} to Gemini: {e}")
            return {"text": f"[Error uploading file: {filename}]"}

    @staticmethod
    def build_file_contents_for_gemini(job_files: List[JobFile]) -> List[Any]:
        """
        Build list of file contents for Gemini API from multiple files.

        Args:
            job_files: List of JobFile instances

        Returns:
            List of Gemini File objects or content dictionaries
        """
        file_contents = []

        for job_file in job_files:
            content = ChatFileService.build_file_content_for_gemini(job_file)
            file_contents.append(content)

        logger.debug(f"Built content for {len(file_contents)} files")
        return file_contents
