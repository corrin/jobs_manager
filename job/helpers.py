import decimal
import json
import logging
import os
import uuid
from decimal import Decimal

from django.conf import settings
from workflow.models.company_defaults import CompanyDefaults


def get_job_folder_path(job_number):
    """Get the absolute filesystem path for a job's folder."""
    return os.path.join(settings.DROPBOX_WORKFLOW_FOLDER, f"Job-{job_number}")


def get_company_defaults():
    """Retrieve the single CompanyDefaults instance using the singleton pattern."""
    return CompanyDefaults.get_instance()


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        elif isinstance(obj, uuid.UUID):
            logging.error("You found a bug! UUIDs should not be here. UUID: %s", obj)
            return str(obj)
        return super(DecimalEncoder, self).default(obj)


def decimal_to_float(value):
    return float(value) if isinstance(value, Decimal) else value
