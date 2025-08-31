import logging
import os

from django.conf import settings
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.renderers import BaseRenderer, JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.job.mixins import JobLookupMixin, JobNumberLookupMixin
from apps.job.models import JobFile
from apps.job.serializers.job_file_serializer import (
    JobFileErrorResponseSerializer,
    JobFileSerializer,
    JobFileThumbnailErrorResponseSerializer,
    JobFileUpdateSuccessResponseSerializer,
    JobFileUploadPartialResponseSerializer,
    JobFileUploadSuccessResponseSerializer,
)
from apps.workflow.services.error_persistence import persist_app_error

logger = logging.getLogger(__name__)


class BinaryFileRenderer(BaseRenderer):
    media_type = "*/*"
    format = "file"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data


class JobFileView(JobNumberLookupMixin, APIView):
    """
    API view for managing job files including upload, download, update, and deletion.
    """

    renderer_classes = [JSONRenderer, BinaryFileRenderer]
    serializer_class = JobFileSerializer

    def save_file(self, job, file_obj, print_on_jobsheet, request):
        """
        Save file to disk and create or update JobFile record.
        This operation is atomic and will raise an exception on any failure.
        """
        job_folder = os.path.join(
            settings.DROPBOX_WORKFLOW_FOLDER, f"Job-{job.job_number}"
        )
        os.makedirs(job_folder, exist_ok=True)
        file_path = os.path.join(job_folder, file_obj.name)

        logger.info(
            "Attempting to save file for job %s",
            job.job_number,
            extra={
                "operation": "save_file",
                "upload_filename": file_obj.name,
                "job_id": str(job.id),
            },
        )

        # Fail early if the uploaded file is empty.
        if file_obj.size == 0:
            raise ValueError(f"Uploaded file {file_obj.name} is empty (0 bytes).")

        try:
            # Write the file to the designated workflow folder.
            with open(file_path, "wb") as destination:
                for chunk in file_obj.chunks():
                    destination.write(chunk)

            # Create or update the database record for the file.
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
                "%s JobFile record: %s",
                "Created" if created else "Updated",
                job_file.filename,
                extra={
                    "operation": "save_file",
                    "job_id": str(job.id),
                    "status": "success",
                },
            )

            # Generate a thumbnail for image files.
            if file_obj.content_type and file_obj.content_type.startswith("image/"):
                from apps.job.services.file_service import (
                    create_thumbnail,
                    get_thumbnail_folder,
                )

                thumb_folder = get_thumbnail_folder(job.job_number)
                thumb_path = os.path.join(thumb_folder, f"{file_obj.name}.thumb.jpg")
                create_thumbnail(file_path, thumb_path)
                logger.info("Thumbnail created successfully: %s", thumb_path)

            # Return the serialized data of the created/updated file record.
            return JobFileSerializer(job_file, context={"request": request}).data

        except Exception as e:
            # Persist any unexpected error during the file operation and re-raise it.
            logger.error(
                "Error processing file %s",
                file_obj.name,
                extra={
                    "operation": "save_file",
                    "job_id": str(job.id),
                    "status": "error",
                },
                exc_info=True,
            )
            persist_app_error(
                e,
                request=request,
                context={"job_id": str(job.id), "upload_filename": file_obj.name},
            )
            raise

    @extend_schema(
        operation_id="uploadJobFilesApi",
        responses={
            201: JobFileUploadSuccessResponseSerializer,
            207: JobFileUploadPartialResponseSerializer,
            400: JobFileErrorResponseSerializer,
        },
    )
    def post(self, request, job_number=None):
        """Handle file uploads for a job."""
        job, error_response = self.get_job_or_404_response(job_number=job_number)
        if error_response:
            return error_response

        files = request.FILES.getlist("files")
        if not files:
            return Response(
                {"status": "error", "message": "No files were provided for upload."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        print_on_jobsheet = True
        uploaded_files, errors = [], []

        for file_obj in files:
            try:
                # The save_file function is atomic and will raise an exception on failure.
                result = self.save_file(job, file_obj, print_on_jobsheet, request)
                uploaded_files.append(result)
            except Exception as e:
                # Catch the exception raised by save_file to build a multi-status response.
                errors.append(f"Failed to upload {file_obj.name}: {str(e)}")

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
                "message": "Files uploaded successfully.",
            },
            status=status.HTTP_201_CREATED,
        )

    def _get_by_number(self, job_number):
        """Return the list of active files for a given job."""
        job, error_response = self.get_job_or_404_response(job_number=job_number)
        if error_response:
            return error_response

        qs = JobFile.objects.filter(job=job, status="active")
        serializer = JobFileSerializer(qs, many=True, context={"request": self.request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def _get_by_path(self, file_path):
        """Serve a specific file for download or inline viewing."""
        full_path = os.path.join(settings.DROPBOX_WORKFLOW_FOLDER, file_path)

        if not os.path.exists(full_path):
            return Response(
                {"status": "error", "message": "File not found at the specified path."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            import mimetypes

            response = FileResponse(open(full_path, "rb"))
            content_type, _ = mimetypes.guess_type(full_path)
            if content_type:
                response["Content-Type"] = content_type
            response[
                "Content-Disposition"
            ] = f'inline; filename="{os.path.basename(file_path)}"'
            return response
        except Exception as e:
            # Persist any error that occurs while trying to serve the file.
            logger.exception(f"Error serving file {file_path}")
            persist_app_error(e, request=self.request, context={"file_path": file_path})
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        operation_id="retrieveJobFilesApi",
        responses={
            200: JobFileSerializer(many=True),
            404: JobFileErrorResponseSerializer,
            400: JobFileErrorResponseSerializer,
        },
    )
    def get(self, request, file_path=None, job_number=None):
        """Route the request to serve a file or list files for a job."""
        if job_number:
            return self._get_by_number(job_number)
        elif file_path:
            return self._get_by_path(file_path)
        else:
            return Response(
                {
                    "status": "error",
                    "message": "A job_number or file_path parameter is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    @extend_schema(
        operation_id="updateJobFilesApi",
        responses={
            200: JobFileUpdateSuccessResponseSerializer,
            400: JobFileErrorResponseSerializer,
            404: JobFileErrorResponseSerializer,
        },
    )
    def put(self, request, job_number=None):
        """Update an existing job file's content or its metadata."""
        job, error_response = self.get_job_or_404_response(job_number=job_number)
        if error_response:
            return error_response

        filename = request.data.get("filename")
        if not filename:
            return Response(
                {
                    "status": "error",
                    "message": "A 'filename' is required to identify the file to update.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        job_file = get_object_or_404(JobFile, job=job, filename=filename)
        print_on_jobsheet = str(
            request.data.get("print_on_jobsheet", job_file.print_on_jobsheet)
        ).lower() in ["true", "1"]
        file_obj = request.FILES.get("files")

        try:
            if file_obj:
                # If a file is provided, overwrite the existing file content.
                if file_obj.size == 0:
                    raise ValueError("The new file cannot be 0 bytes.")

                full_path = os.path.join(
                    settings.DROPBOX_WORKFLOW_FOLDER, job_file.file_path
                )
                with open(full_path, "wb") as destination:
                    for chunk in file_obj.chunks():
                        destination.write(chunk)

                if file_obj.content_type and file_obj.content_type.startswith("image/"):
                    from apps.job.services.file_service import (
                        create_thumbnail,
                        get_thumbnail_folder,
                    )

                    thumb_folder = get_thumbnail_folder(job.job_number)
                    thumb_path = os.path.join(
                        thumb_folder, f"{file_obj.name}.thumb.jpg"
                    )
                    create_thumbnail(full_path, thumb_path)

            # Update the print setting regardless of whether a new file was uploaded.
            job_file.print_on_jobsheet = print_on_jobsheet
            job_file.save()

            logger.info(
                "Successfully updated file: %s for job %s",
                filename,
                job_number,
                extra={
                    "operation": "update_file",
                    "job_id": str(job.id),
                    "status": "success",
                },
            )

            return Response(
                {
                    "status": "success",
                    "message": "File updated successfully.",
                    "print_on_jobsheet": job_file.print_on_jobsheet,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            # Persist any error during the update process.
            logger.exception("Error updating file %s for job %s", filename, job_number)
            persist_app_error(
                e,
                request=request,
                context={"job_id": str(job.id), "upload_filename": filename},
            )
            return Response(
                {"status": "error", "message": f"Error updating file: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        operation_id="deleteJobFilesApi",
        responses={
            204: None,
            404: JobFileErrorResponseSerializer,
            500: JobFileErrorResponseSerializer,
        },
    )
    def delete(self, request, file_path=None):
        """Delete a job file by its ID. (Note: file_path param is the job_file.id)."""
        job_file_id = file_path
        try:
            job_file = JobFile.objects.get(id=job_file_id)
            full_path = os.path.join(
                settings.DROPBOX_WORKFLOW_FOLDER, job_file.file_path
            )

            # Delete the physical file from disk if it exists.
            if os.path.exists(full_path):
                os.remove(full_path)
                logger.info("Deleted file from disk: %s", full_path)

            # Delete the database record.
            job_file.delete()
            logger.info(
                "Deleted JobFile record: %s",
                job_file_id,
                extra={
                    "operation": "delete_file",
                    "job_file_id": job_file_id,
                    "status": "success",
                },
            )
            return Response(status=status.HTTP_204_NO_CONTENT)

        except JobFile.DoesNotExist:
            return Response(
                {"status": "error", "message": "File not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            # Persist any other error that occurs during deletion.
            logger.exception("Error deleting file with ID %s", job_file_id)
            persist_app_error(e, request=request, context={"job_file_id": job_file_id})
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class JobFileThumbnailView(JobLookupMixin, APIView):
    """API view for serving JPEG thumbnails of job files."""

    lookup_url_kwarg = "file_id"
    serializer_class = JobFileThumbnailErrorResponseSerializer

    @extend_schema(operation_id="getJobFileThumbnail")
    def get(self, request, file_id):
        job_file = get_object_or_404(JobFile, id=file_id, status="active")
        thumb_path = job_file.thumbnail_path

        if not thumb_path or not os.path.exists(thumb_path):
            return Response(
                {"status": "error", "message": "Thumbnail not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            return FileResponse(open(thumb_path, "rb"), content_type="image/jpeg")
        except Exception as e:
            # Persist errors related to serving the thumbnail file.
            logger.exception("Error serving thumbnail for file ID %s", file_id)
            persist_app_error(e, request=request, context={"job_file_id": file_id})
            return Response(
                {"status": "error", "message": "Could not serve thumbnail file."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
