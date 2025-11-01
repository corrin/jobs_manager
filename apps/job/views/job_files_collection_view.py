"""
Job Files Collection View - Collection operations on /jobs/{job_id}/files/

Handles:
- POST: Upload files to a job
- GET: List all files for a job

All identifiers (job_id) are in URL path, NOT request body.
"""

import logging
import os

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.job.mixins import JobLookupMixin
from apps.job.models import JobFile
from apps.job.serializers.job_file_serializer import (
    JobFileErrorResponseSerializer,
    JobFileSerializer,
    JobFileUploadPartialResponseSerializer,
    JobFileUploadSuccessResponseSerializer,
)
from apps.workflow.services.error_persistence import persist_app_error

logger = logging.getLogger(__name__)


class JobFilesCollectionView(JobLookupMixin, APIView):
    """
    Collection operations on job files.

    URL: /rest/jobs/{job_id}/files/
    Methods: POST (upload), GET (list)
    """

    parser_classes = [MultiPartParser, FormParser]
    serializer_class = JobFileSerializer

    def save_file(self, job, file_obj, print_on_jobsheet, request):
        """Save file to disk and create JobFile record."""
        job_folder = os.path.join(
            settings.DROPBOX_WORKFLOW_FOLDER, f"Job-{job.job_number}"
        )
        os.makedirs(job_folder, exist_ok=True)
        file_path = os.path.join(job_folder, file_obj.name)

        # Fail early if empty
        if file_obj.size == 0:
            raise ValueError(f"Uploaded file {file_obj.name} is empty (0 bytes)")

        try:
            # Write file
            with open(file_path, "wb") as destination:
                for chunk in file_obj.chunks():
                    destination.write(chunk)

            # Create database record
            relative_path = os.path.relpath(file_path, settings.DROPBOX_WORKFLOW_FOLDER)
            job_file, created = JobFile.objects.update_or_create(
                job=job,
                filename=file_obj.name,
                defaults={
                    "file_path": relative_path,
                    "mime_type": file_obj.content_type,
                    "print_on_jobsheet": print_on_jobsheet,
                },
            )

            logger.info(
                "%s file: %s for job %s",
                "Created" if created else "Updated",
                file_obj.name,
                job.job_number,
            )

            # Generate thumbnail for images
            if file_obj.content_type and file_obj.content_type.startswith("image/"):
                from apps.job.services.file_service import (
                    create_thumbnail,
                    get_thumbnail_folder,
                )

                thumb_folder = get_thumbnail_folder(job.job_number)
                thumb_path = os.path.join(thumb_folder, f"{file_obj.name}.thumb.jpg")
                create_thumbnail(file_path, thumb_path)

            return JobFileSerializer(job_file, context={"request": request}).data

        except Exception as e:
            logger.error("Error saving file %s: %s", file_obj.name, str(e))
            persist_app_error(
                e,
                request=request,
                context={"job_id": str(job.id), "filename": file_obj.name},
            )
            raise

    @extend_schema(
        operation_id="uploadJobFiles",
        responses={
            201: JobFileUploadSuccessResponseSerializer,
            207: JobFileUploadPartialResponseSerializer,
            400: JobFileErrorResponseSerializer,
        },
        description="Upload files to a job. Job ID (UUID) is in URL path.",
        tags=["Job Files"],
    )
    def post(self, request, job_id):
        """Upload files to a job."""
        # Get job from URL parameter
        job, error_response = self.get_job_or_404_response()
        if error_response:
            return error_response

        # Get files from request
        files = request.FILES.getlist("files")
        if not files:
            return Response(
                {"status": "error", "message": "No files provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        print_on_jobsheet = True
        uploaded_files, errors = [], []

        # Process each file
        for file_obj in files:
            try:
                result = self.save_file(job, file_obj, print_on_jobsheet, request)
                uploaded_files.append(result)
            except Exception as e:
                errors.append(f"Failed to upload {file_obj.name}: {str(e)}")

        # Return response
        if errors:
            response_status = (
                status.HTTP_207_MULTI_STATUS
                if uploaded_files
                else status.HTTP_400_BAD_REQUEST
            )
            response_data = {
                "status": "partial_success" if uploaded_files else "error",
                "uploaded": uploaded_files,
                "errors": errors,
            }
            return Response(response_data, status=response_status)

        return Response(
            {
                "status": "success",
                "uploaded": uploaded_files,
                "message": "Files uploaded successfully",
            },
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        operation_id="listJobFiles",
        responses={
            200: JobFileSerializer(many=True),
            404: JobFileErrorResponseSerializer,
        },
        description="List all active files for a job.",
        tags=["Job Files"],
    )
    def get(self, request, job_id):
        """List files for a job."""
        # Get job from URL parameter
        job, error_response = self.get_job_or_404_response()
        if error_response:
            return error_response

        # Get active files
        files = JobFile.objects.filter(job=job, status="active")
        serializer = JobFileSerializer(files, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)
