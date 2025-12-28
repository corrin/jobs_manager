import decimal
import json
import os
from decimal import Decimal

from django.conf import settings


def get_job_folder_path(job_number: str) -> str:
    """Get the absolute filesystem path for a job's folder."""
    return os.path.join(settings.DROPBOX_WORKFLOW_FOLDER, f"Job-{job_number}")


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj: object) -> object:
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


def decimal_to_float(value: Decimal | float | int) -> float:
    return float(value)
