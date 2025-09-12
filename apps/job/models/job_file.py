import os
import uuid

from django.db import models

from apps.job.helpers import get_job_folder_path
from apps.job.services.file_service import get_thumbnail_folder


class JobFile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey("Job", related_name="files", on_delete=models.CASCADE)
    filename = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)
    mime_type = models.CharField(max_length=100, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[("active", "Active"), ("deleted", "Deleted")],
        default="active",
    )
    print_on_jobsheet = models.BooleanField(default=True)

    @property
    def full_path(self):
        """Full system path to the file."""
        return get_job_folder_path(self.job.job_number)

    @property
    def url(self):
        """URL to serve the file (if using Django to serve media)."""
        return f"/jobs/files/{self.file_path}"  # We'll need to add this URL pattern

    @property
    def thumbnail_path(self):
        """Return path to thumbnail if one exists."""
        if self.status == "deleted":
            return None

        thumb_path = os.path.join(
            get_thumbnail_folder(self.job.job_number), f"{self.filename}.thumb.jpg"
        )
        return thumb_path if os.path.exists(thumb_path) else None

    @property
    def size(self):
        """Return size of file in bytes."""
        if self.status == "deleted":
            return None

        file_path = os.path.join(self.full_path, self.filename)
        return os.path.getsize(file_path) if os.path.exists(file_path) else None

    class Meta:
        db_table = "workflow_jobfile"
        ordering = ["-uploaded_at"]
