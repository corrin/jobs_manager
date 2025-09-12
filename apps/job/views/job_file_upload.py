import logging
import os

# Use django.conf.settings to access the fully configured Django settings
# This ensures we get settings after all imports and env vars are processed
from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.job.mixins import JobNumberLookupMixin
from apps.job.models import JobFile
from apps.job.serializers.job_file_serializer import (
    JobFileErrorResponseSerializer,
    JobFileSerializer,
    JobFileUploadViewResponseSerializer,
)

logger = logging.getLogger(__name__)


class JobFileUploadView(JobNumberLookupMixin, APIView):
    """
    REST API view for uploading files to jobs.

    Handles multipart file uploads, saves files to the Dropbox workflow folder,
    and creates JobFile database records with proper file metadata.
    """

    parser_classes = [MultiPartParser, FormParser]
    serializer_class = JobFileUploadViewResponseSerializer

    @extend_schema(operation_id="uploadJobFilesRest")
    def post(self, request):
        job_number = request.data.get("job_number")
        if not job_number:
            error_response = {"status": "error", "message": "Job number is required"}
            error_serializer = JobFileErrorResponseSerializer(error_response)
            return Response(error_serializer.data, status=status.HTTP_400_BAD_REQUEST)

        files = request.FILES.getlist("files")
        if not files:
            error_response = {"status": "error", "message": "No files uploaded"}
            error_serializer = JobFileErrorResponseSerializer(error_response)
            return Response(error_serializer.data, status=status.HTTP_400_BAD_REQUEST)

        # Validate job exists first
        job_obj, error_response = self.get_job_or_404_response(
            job_number=job_number, error_format="legacy"
        )
        if error_response:
            return error_response

        # Define the Dropbox sync folder path
        job_folder = os.path.join(settings.DROPBOX_WORKFLOW_FOLDER, f"Job-{job_number}")
        os.makedirs(job_folder, exist_ok=True)

        os.chmod(job_folder, 0o2775)

        uploaded_instances = []
        # Save each uploaded file
        for file in files:
            file_path = os.path.join(job_folder, file.name)
            with open(file_path, "wb") as destination:
                for chunk in file.chunks():
                    destination.write(chunk)
                os.chmod(file_path, 0o664)

            relative_path = os.path.relpath(file_path, settings.DROPBOX_WORKFLOW_FOLDER)
            job_file, created = JobFile.objects.update_or_create(
                job=job_obj,
                filename=file.name,
                defaults={
                    "file_path": relative_path,
                    "mime_type": file.content_type,
                    "print_on_jobsheet": False,
                    "status": "active",
                },
            )
            uploaded_instances.append(job_file)

        serializer = JobFileSerializer(
            uploaded_instances, many=True, context={"request": request}
        )

        response_data = {
            "status": "success",
            "uploaded": serializer.data,
            "message": "Files uploaded successfully",
        }

        response_serializer = JobFileUploadViewResponseSerializer(response_data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
