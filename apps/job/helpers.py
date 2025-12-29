import os

from django.conf import settings


def get_job_folder_path(job_number: str) -> str:
    """Get the absolute filesystem path for a job's folder."""
    return os.path.join(settings.DROPBOX_WORKFLOW_FOLDER, f"Job-{job_number}")
