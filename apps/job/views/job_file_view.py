import logging
import os

from django.conf import settings
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.renderers import BaseRenderer, JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.job.mixins import JobLookupMixin, JobNumberLookupMixin
from apps.job.models import Job, JobFile
from apps.job.serializers.job_file_serializer import JobFileSerializer

logger = logging.getLogger(__name__)


class BinaryFileRenderer(BaseRenderer):
    media_type = "*/*"
    format = "file"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data


class JobFileView(JobNumberLookupMixin, APIView):
    renderer_classes = [JSONRenderer, BinaryFileRenderer]

    def save_file(self, job, file_obj, print_on_jobsheet):
        """
        Save file to disk and create or update JobFile record.
        """
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
            return {
                "id": str(job_file.id),
                "filename": job_file.filename,
                "file_path": job_file.file_path,
                "print_on_jobsheet": job_file.print_on_jobsheet,
            }
        except Exception as e:
            logger.exception("Error processing file %s: %s", file_obj.name, str(e))
            return {"error": f"Error uploading {file_obj.name}: {str(e)}"}

    def post(self, request):
        """
        Handle file uploads. Creates new files or updates existing ones with POST.
        """
        logger.debug("Processing POST request to upload files (creating new).")

        job, error_response = self.get_job_from_request_data(
            request, error_format="legacy"
        )
        if error_response:
            return error_response

        files = request.FILES.getlist("files")
        if not files:
            return Response(
                {"status": "error", "message": "No files uploaded"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        print_on_jobsheet = True
        uploaded_files = []
        errors = []

        for file_obj in files:
            result = self.save_file(job, file_obj, print_on_jobsheet)
            if "error" in result:
                errors.append(result["error"])
            else:
                uploaded_files.append(result)

        if errors:
            return Response(
                {
                    "status": "partial_success" if uploaded_files else "error",
                    "uploaded": uploaded_files,
                    "errors": errors,
                },
                status=(
                    status.HTTP_207_MULTI_STATUS
                    if uploaded_files
                    else status.HTTP_400_BAD_REQUEST
                ),
            )

        return Response(
            {
                "status": "success",
                "uploaded": uploaded_files,
                "message": "Files uploaded successfully",
            },
            status=status.HTTP_201_CREATED,
        )

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
            return Response(
                {"status": "error", "message": "File not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            response = FileResponse(open(full_path, "rb"))

            import mimetypes

            content_type, _ = mimetypes.guess_type(full_path)
            if content_type:
                response["Content-Type"] = content_type

            response["Content-Disposition"] = (
                f'inline; filename="{os.path.basename(file_path)}"'
            )
            return response
        except Exception as e:
            logger.exception(f"Error serving file {file_path}")
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
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
            return Response(
                {
                    "status": "error",
                    "message": "Invalid request, provide file_path or job_number",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    def put(self, request):
        """
        Update an existing job file:
        - If a new file is provided (files[] in request), replace the file on disk.
        - If no file_obj is provided, only update print_on_jobsheet.
        """
        logger.debug(
            "Processing PUT request to update an existing file or its print_on_jobsheet."
        )

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

            return Response(
                {"status": "success", "message": "Updated print_on_jobsheet only"},
                status=status.HTTP_200_OK,
            )

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
            return Response(
                {"status": "error", "message": "File not found for update"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if file_obj.size == 0:
            logger.warning("PUT aborted because new file is 0 bytes: %s", file_obj.name)
            return Response(
                {"status": "error", "message": "New file is 0 bytes, update aborted."},
                status=status.HTTP_400_BAD_REQUEST,
            )

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
                return Response(
                    {"status": "error", "message": "File got truncated or incomplete."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            old_print_value = job_file.print_on_jobsheet
            job_file.print_on_jobsheet = print_on_jobsheet
            job_file.save()

            logger.info(
                "Successfully updated file: %s (print_on_jobsheet %s->%s).",
                file_obj.name,
                old_print_value,
                print_on_jobsheet,
            )
            return Response(
                {
                    "status": "success",
                    "message": "File updated successfully",
                    "print_on_jobsheet": job_file.print_on_jobsheet,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.exception("Error updating file %s: %s", file_path, str(e))
            return Response(
                {"status": "error", "message": f"Error updating file: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
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
            return Response(
                {"status": "error", "message": "File not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            logger.exception("Error deleting file %s", file_path)
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class JobFileThumbnailView(JobLookupMixin, APIView):
    lookup_url_kwarg = "file_id"  # Note: this view uses file_id, not job_id
    """
    Serve a JPEG thumbnail of a JobFile via its UUID
    """

    def get(self, request, file_id):
        job_file = get_object_or_404(JobFile, id=file_id, status="active")
        thumb = job_file.thumbnail_path
        if not thumb or not os.path.exists(thumb):
            return Response(
                {"status": "error", "message": "Thumbnail not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        return FileResponse(open(thumb, "rb"), content_type="image/jpeg")
