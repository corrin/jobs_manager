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

logger = logging.getLogger(__name__)


class BinaryFileRenderer(BaseRenderer):
    media_type = "*/*"
    format = "file"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data


class JobFileView(JobNumberLookupMixin, APIView):
    """
    API view for managing job files including upload, download, update, and deletion.

    This view handles file operations for jobs including:
    - POST: Upload new files to a job
    - GET: Retrieve file list for a job or serve a specific file for download
    - PUT: Update existing files or their print_on_jobsheet setting
    - DELETE: Remove files from a job

    Files are stored in the Dropbox workflow folder and tracked in the database
    via JobFile model instances. Supports both replacing file content and updating
    metadata like print_on_jobsheet flag for workshop printing.
    """

    renderer_classes = [JSONRenderer, BinaryFileRenderer]
    serializer_class = JobFileSerializer

    def get_serializer_class(self):
        """Return the appropriate serializer class based on the request method"""
        if self.request.method == "POST":
            return JobFileUploadSuccessResponseSerializer
        elif self.request.method == "PUT":
            return JobFileUpdateSuccessResponseSerializer
        return JobFileSerializer

    def save_file(self, job, file_obj, print_on_jobsheet):
        """
        Save file to disk and create or update JobFile record.
        """
        from apps.workflow.services.error_persistence import persist_app_error

        job_folder = os.path.join(
            settings.DROPBOX_WORKFLOW_FOLDER, f"Job-{job.job_number}"
        )
        os.makedirs(job_folder, exist_ok=True)

        file_path = os.path.join(job_folder, file_obj.name)
        logger.info(
            "Attempting to save file: %s for job %s", file_obj.name, job.job_number
        )

        # Extra logging before writing
        logger.debug("File size (bytes) received from client: %d", file_obj.size)

        # If file_obj.size is 0, we can abort or raise a warning:
        if file_obj.size == 0:
            logger.warning(
                "Aborting save because the uploaded file size is 0 bytes: %s",
                file_obj.name,
            )
            return {
                "error": f"Uploaded file {file_obj.name} is empty (0 bytes), not saved."
            }

        job_file = None  # Initialize to avoid UnboundLocalError

        try:
            bytes_written = 0
            with open(file_path, "wb") as destination:
                for chunk in file_obj.chunks():
                    destination.write(chunk)
                    bytes_written += len(chunk)

            logger.info("Wrote %d bytes to disk at %s", bytes_written, file_path)

            # Check final file size on disk
            file_size_on_disk = os.path.getsize(file_path)
            if file_size_on_disk < file_obj.size:
                logger.error(
                    "File on disk is smaller than expected! (on disk: %d, expected: %d)",
                    file_size_on_disk,
                    file_obj.size,
                )
                return {"error": f"File {file_obj.name} is corrupted or incomplete."}
            else:
                logger.debug("File on disk verified with correct size.")

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
                "%s JobFile: %s (print_on_jobsheet=%s)",
                "Created" if created else "Updated",
                job_file.filename,
                job_file.print_on_jobsheet,
            )

            # Prepare success response data
            success_response = {
                "id": str(job_file.id),
                "filename": job_file.filename,
                "file_path": job_file.file_path,
                "print_on_jobsheet": job_file.print_on_jobsheet,
            }

            # Generate thumbnail if it's an image file
            if file_obj.content_type and file_obj.content_type.startswith("image/"):
                from apps.job.services.file_service import (
                    create_thumbnail,
                    get_thumbnail_folder,
                )

                thumb_folder = get_thumbnail_folder(job.job_number)
                thumb_path = os.path.join(thumb_folder, f"{file_obj.name}.thumb.jpg")

                if os.path.exists(thumb_path):
                    logger.debug("Thumbnail already exists: %s", thumb_path)
                    return success_response

                logger.info("Creating thumbnail for %s", file_obj.name)

                try:
                    create_thumbnail(file_path, thumb_path)
                    logger.info("Thumbnail created successfully: %s", thumb_path)

                except Exception as e:
                    # I'm returning the file even if we can't generate the thumbnail
                    # because we are already returning the whole file which can be downloaded anyway
                    logger.error(
                        "Failed to create thumbnail for %s: %s", file_obj.name, str(e)
                    )
                    persist_app_error(
                        e,
                        context={
                            "job_id": str(job_file.job.id),
                            "filename": file_obj.name,
                        },
                    )

            # Return success response for both image and non-image files
            return success_response

        except Exception as e:
            logger.exception("Error processing file %s: %s", file_obj.name, str(e))
            # Persist error following defensive programming rules
            persist_app_error(
                e, context={"job_id": str(job.id), "filename": file_obj.name}
            )
            return {"error": f"Error uploading {file_obj.name}: {str(e)}"}

    @extend_schema(
        operation_id="uploadJobFilesApi",
        responses={
            201: JobFileUploadSuccessResponseSerializer,
            207: JobFileUploadPartialResponseSerializer,
            400: JobFileErrorResponseSerializer,
        },
    )
    def post(self, request, job_number=None):
        """
        Handle file uploads. Creates new files or updates existing ones with POST.
        """
        logger.debug("Processing POST request to upload files (creating new).")

        # Accept job_number from URL parameter or request data
        if job_number:
            job, error_response = self.get_job_or_404_response(
                job_number=job_number, error_format="legacy"
            )
        else:
            job, error_response = self.get_job_from_request_data(
                request, error_format="legacy"
            )

        if error_response:
            return error_response

        files = request.FILES.getlist("files")
        if not files:
            error_response = {"status": "error", "message": "No files uploaded"}
            error_serializer = JobFileErrorResponseSerializer(error_response)
            return Response(error_serializer.data, status=status.HTTP_400_BAD_REQUEST)

        print_on_jobsheet = True
        uploaded_files = []
        errors = []

        for file_obj in files:
            result = self.save_file(job, file_obj, print_on_jobsheet)

            # Defensive programming: ensure result is not None
            if result is None:
                logger.error("save_file returned None for file: %s", file_obj.name)
                errors.append(f"Internal error processing file {file_obj.name}")
                continue

            # Defensive programming: ensure result is a dictionary
            if not isinstance(result, dict):
                logger.error(
                    "save_file returned non-dict result for file: %s, result: %s",
                    file_obj.name,
                    result,
                )
                errors.append(f"Internal error processing file {file_obj.name}")
                continue

            if "error" in result:
                errors.append(result["error"])
            else:
                uploaded_files.append(result)

        if errors:
            if uploaded_files:
                response_data = {
                    "status": "partial_success",
                    "uploaded": uploaded_files,
                    "errors": errors,
                }
                partial_serializer = JobFileUploadPartialResponseSerializer(
                    response_data
                )
                return Response(
                    partial_serializer.data, status=status.HTTP_207_MULTI_STATUS
                )
            else:
                response_data = {
                    "status": "error",
                    "uploaded": uploaded_files,
                    "errors": errors,
                }
                error_serializer = JobFileUploadPartialResponseSerializer(response_data)
                return Response(
                    error_serializer.data, status=status.HTTP_400_BAD_REQUEST
                )

        response_data = {
            "status": "success",
            "uploaded": uploaded_files,
            "message": "Files uploaded successfully",
        }
        success_serializer = JobFileUploadSuccessResponseSerializer(response_data)
        return Response(success_serializer.data, status=status.HTTP_201_CREATED)

    def _get_by_number(self, job_number):
        """
        Return the file list of a job.
        """
        job, error_response = self.get_job_or_404_response(
            job_number=job_number, error_format="legacy"
        )
        if error_response:
            return error_response

        qs = JobFile.objects.filter(job=job, status="active")
        serializer = JobFileSerializer(qs, many=True, context={"request": self.request})
        return Response(serializer.data, status=200)

    def _get_by_path(self, file_path):
        """
        Serve a specific file for download.
        """
        full_path = os.path.join(settings.DROPBOX_WORKFLOW_FOLDER, file_path)

        if not os.path.exists(full_path):
            error_response = {"status": "error", "message": "File not found"}
            error_serializer = JobFileErrorResponseSerializer(error_response)
            return Response(error_serializer.data, status=status.HTTP_404_NOT_FOUND)

        try:
            response = FileResponse(open(full_path, "rb"))

            import mimetypes

            content_type, _ = mimetypes.guess_type(full_path)
            if content_type:
                response["Content-Type"] = content_type

            response[
                "Content-Disposition"
            ] = f'inline; filename="{os.path.basename(file_path)}"'
            return response
        except Exception as e:
            logger.exception(f"Error serving file {file_path}")
            error_response = {"status": "error", "message": str(e)}
            error_serializer = JobFileErrorResponseSerializer(error_response)
            return Response(
                error_serializer.data, status=status.HTTP_500_INTERNAL_SERVER_ERROR
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
        """
        Based on the request, serve a file for download or return the file list of the job.
        """
        if job_number:
            return self._get_by_number(job_number)
        elif file_path:
            return self._get_by_path(file_path)
        else:
            error_response = {
                "status": "error",
                "message": "Invalid request, provide file_path or job_number",
            }
            error_serializer = JobFileErrorResponseSerializer(error_response)
            return Response(error_serializer.data, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        operation_id="updateJobFilesApi",
        responses={
            200: JobFileUpdateSuccessResponseSerializer,
            400: JobFileErrorResponseSerializer,
            404: JobFileErrorResponseSerializer,
            500: JobFileErrorResponseSerializer,
        },
    )
    def put(self, request, job_number=None):
        """
        Update an existing job file:
        - If a new file is provided (files[] in request), replace the file on disk.
        - If no file_obj is provided, only update print_on_jobsheet.
        """
        logger.debug(
            "Processing PUT request to update an existing file or its print_on_jobsheet."
        )

        # Accept job_number from URL parameter or request data
        if not job_number:
            job_number = request.data.get("job_number")

        print_on_jobsheet = str(request.data.get("print_on_jobsheet")) in [
            "true",
            "True",
            "1",
        ]

        job, error_response = self.get_job_or_404_response(
            job_number=job_number, error_format="legacy"
        )
        if error_response:
            return error_response

        file_obj = request.FILES.get("files")
        if not file_obj:
            # Case 1: No file provided, only update print_on_jobsheet
            logger.debug(
                "No file in PUT request, so only updating print_on_jobsheet => %s",
                print_on_jobsheet,
            )

            # We need to know which JobFile we're updating, and currently the front-end is sending the filename.
            filename = request.data.get("filename")  # Ex.: "test.jpeg"
            if not filename:
                return Response(
                    {
                        "status": "error",
                        "message": "Filename is required to update print_on_jobsheet.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            job_file = JobFile.objects.filter(job=job, filename=filename).first()
            if not job_file:
                return Response(
                    {"status": "error", "message": "File not found for update"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            old_value = job_file.print_on_jobsheet
            job_file.print_on_jobsheet = print_on_jobsheet
            job_file.save()
            logger.info(
                "Updated print_on_jobsheet from %s to %s for file %s",
                old_value,
                print_on_jobsheet,
                filename,
            )

            response_data = {
                "status": "success",
                "message": "Updated print_on_jobsheet only",
                "print_on_jobsheet": print_on_jobsheet,
            }
            success_serializer = JobFileUpdateSuccessResponseSerializer(response_data)
            return Response(success_serializer.data, status=status.HTTP_200_OK)

        # Case 2: File provided, overwrite the file + update print_on_jobsheet
        logger.info(
            "PUT update for job #%s, file: %s, size: %d bytes",
            job_number,
            file_obj.name,
            file_obj.size,
        )

        # Check if this file exists in the job:
        job_file = JobFile.objects.filter(job=job, filename=file_obj.name).first()
        if not job_file:
            logger.error(
                "File not found for update: %s in job %s", file_obj.name, job_number
            )
            error_response = {"status": "error", "message": "File not found for update"}
            error_serializer = JobFileErrorResponseSerializer(error_response)
            return Response(error_serializer.data, status=status.HTTP_404_NOT_FOUND)

        if file_obj.size == 0:
            logger.warning("PUT aborted because new file is 0 bytes: %s", file_obj.name)
            error_response = {
                "status": "error",
                "message": "New file is 0 bytes, update aborted.",
            }
            error_serializer = JobFileErrorResponseSerializer(error_response)
            return Response(error_serializer.data, status=status.HTTP_400_BAD_REQUEST)

        file_path = os.path.join(settings.DROPBOX_WORKFLOW_FOLDER, job_file.file_path)
        logger.debug("Overwriting file on disk: %s", file_path)
        try:
            bytes_written = 0
            with open(file_path, "wb") as destination:
                for chunk in file_obj.chunks():
                    destination.write(chunk)
                    bytes_written += len(chunk)

            on_disk = os.path.getsize(file_path)
            logger.info(
                "PUT replaced file: %s, wrote %d bytes (on disk: %d).",
                file_path,
                bytes_written,
                on_disk,
            )

            if on_disk < file_obj.size:
                logger.error(
                    "Updated file is smaller than expected (on_disk=%d < expected=%d).",
                    on_disk,
                    file_obj.size,
                )
                error_response = {
                    "status": "error",
                    "message": "File got truncated or incomplete.",
                }
                error_serializer = JobFileErrorResponseSerializer(error_response)
                return Response(
                    error_serializer.data, status=status.HTTP_400_BAD_REQUEST
                )

            old_print_value = job_file.print_on_jobsheet
            job_file.print_on_jobsheet = print_on_jobsheet
            job_file.save()

            # Generate thumbnail if it's an image file
            if file_obj.content_type and file_obj.content_type.startswith("image/"):
                from apps.job.services.file_service import (
                    create_thumbnail,
                    get_thumbnail_folder,
                )

                thumb_folder = get_thumbnail_folder(job.job_number)
                thumb_path = os.path.join(thumb_folder, f"{file_obj.name}.thumb.jpg")

                logger.info("Creating/updating thumbnail for %s", file_obj.name)
                try:
                    create_thumbnail(file_path, thumb_path)
                    logger.info("Thumbnail created successfully: %s", thumb_path)

                except Exception as e:
                    from apps.workflow.services.error_persistence import (
                        persist_app_error,
                    )

                    logger.error("Failed to create thumbnail for %s", file_obj.name)

                    persist_app_error(e, job_id=str(job_file.job.id))

                # I'm returning the file even if we can't generate the thumbnail
                # because the file operation is successfull, the thumbnail shouldn't be mandatory.
                finally:
                    logger.info(
                        "Successfully updated file: %s (print_on_jobsheet %s->%s).",
                        file_obj.name,
                        old_print_value,
                        print_on_jobsheet,
                    )
                    response_data = {
                        "status": "success",
                        "message": "File updated successfully",
                        "print_on_jobsheet": job_file.print_on_jobsheet,
                    }
                    success_serializer = JobFileUpdateSuccessResponseSerializer(
                        response_data
                    )
                    return Response(success_serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception("Error updating file %s: %s", file_path, str(e))
            error_response = {
                "status": "error",
                "message": f"Error updating file: {str(e)}",
            }
            error_serializer = JobFileErrorResponseSerializer(error_response)
            return Response(
                error_serializer.data, status=status.HTTP_500_INTERNAL_SERVER_ERROR
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
        """Delete a job file by its ID. (file_path param is actually the job_file.id)"""
        try:
            job_file = JobFile.objects.get(id=file_path)
            full_path = os.path.join(
                settings.DROPBOX_WORKFLOW_FOLDER, job_file.file_path
            )

            if os.path.exists(full_path):
                os.remove(full_path)
                logger.info("Deleted file from disk: %s", full_path)

            job_file.delete()
            logger.info("Deleted JobFile record: %s", file_path)
            return Response(status=status.HTTP_204_NO_CONTENT)

        except JobFile.DoesNotExist:
            logger.error("JobFile not found with id: %s", file_path)
            error_response = {"status": "error", "message": "File not found"}
            error_serializer = JobFileErrorResponseSerializer(error_response)
            return Response(error_serializer.data, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.exception("Error deleting file %s", file_path)
            error_response = {"status": "error", "message": str(e)}
            error_serializer = JobFileErrorResponseSerializer(error_response)
            return Response(
                error_serializer.data, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class JobFileThumbnailView(JobLookupMixin, APIView):
    """
    API view for serving JPEG thumbnails of job files.

    This view generates and serves thumbnail images for job files that
    support thumbnail generation (typically image files). Thumbnails are
    cached on disk and served via file response for efficient delivery.

    GET: Returns a JPEG thumbnail for the specified file ID, or 404 if
         the thumbnail doesn't exist or cannot be generated.
    """

    lookup_url_kwarg = "file_id"  # Note: this view uses file_id, not job_id
    serializer_class = JobFileThumbnailErrorResponseSerializer

    @extend_schema(operation_id="getJobFileThumbnail")
    def get(self, request, file_id):
        job_file = get_object_or_404(JobFile, id=file_id, status="active")
        thumb = job_file.thumbnail_path
        if not thumb or not os.path.exists(thumb):
            error_response = {"status": "error", "message": "Thumbnail not found"}
            error_serializer = JobFileThumbnailErrorResponseSerializer(error_response)
            return Response(error_serializer.data, status=status.HTTP_404_NOT_FOUND)
        return FileResponse(open(thumb, "rb"), content_type="image/jpeg")
