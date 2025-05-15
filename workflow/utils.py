from datetime import timezone
import uuid
from zoneinfo import ZoneInfo
from django.contrib.messages import get_messages
from django.db import models
from workflow.models import Job
import logging
from django.apps import apps
from django.db.utils import ProgrammingError, OperationalError


logger = logging.getLogger(__name__)

def extract_messages(request):
    """
    Extracts messages from the request object and returns them as a list of
    dictionaries.
    Each dictionary contains the message level tag and the message text.

    Args:
        request: The HTTP request object containing the messages

    Returns:
        list: A list of dictionaries, where each dictionary has:
            - level (str): The message level tag (e.g. 'info', 'error')
            - message (str): The message text
    """

    return [
        {"level": message.level_tag, "message": message.message}
        for message in get_messages(request)
    ]


def get_rate_type_label(multiplier):
    """
    Converts a pay rate multiplier to its corresponding label.

    Args:
        multiplier (float or str): The pay rate multiplier value (0.0, 1.0, 1.5, or 2.0)

    Returns:
        str: The label corresponding to the multiplier:
            - 'Unpaid' for 0.0
            - 'Ord' (Ordinary) for 1.0
            - 'Ovt' (Overtime) for 1.5
            - 'Dt' (Double Time) for 2.0
            - 'Ord' as default for any other value

    Examples:
        >>> get_rate_type_label(1.5)
        'Ovt'
        >>> get_rate_type_label(0.0)
        'Unpaid'
    """

    rate_map = {0.0: "Unpaid", 1.0: "Ord", 1.5: "Ovt", 2.0: "Dt"}

    return rate_map.get(float(multiplier), "Ord")  # Default to 'Ord' if not found


def get_jobs_data(related_jobs):
    """
    Retrieves and formats job data for the given related jobs.

    Args:
        related_jobs (set): A set of Job objects

    Returns:
        list: A list of dictionaries, where each dictionary contains job data:
            - id (str): The job ID
            - job_number (str): The job number
            - name (str): The job name
            - job_display_name (str): The job display name
            - client_name (str): The client name
            - charge_out_rate (float): The charge out rate
    """
    from workflow.models import Job

    jobs = Job.objects.filter(id__in=related_jobs).select_related(
        "client", "latest_estimate_pricing", "latest_reality_pricing"
    )

    job_data = []
    for job in jobs:
        job_data.append(
            {
                "id": str(job.id),
                "job_number": job.job_number,
                "name": job.name,
                "job_display_name": str(job),
                "estimated_hours": (
                    job.latest_estimate_pricing.total_hours
                    if job.latest_estimate_pricing
                    else 0
                ),
                "hours_spent": (
                    job.latest_reality_pricing.total_hours
                    if job.latest_reality_pricing
                    else 0
                ),
                "client_name": job.client.name if job.client else "NO CLIENT!?",
                "charge_out_rate": float(job.charge_out_rate),
                "job_status": job.status,
            }
        )
    return job_data


def is_valid_uuid(value: str) -> bool:
    """Check if the given string is a valid UUID."""
    try:
        uuid.UUID(value)
        return True
    except (ValueError, TypeError):
        return False

def get_active_jobs() -> models.QuerySet[Job]:
    """
    Returns a queryset of Jobs considered active for work or resource assignment
    (e.g., time entry, stock allocation).

    Excludes jobs that are rejected, on hold, completed, or archived.
    This matches the filter used in the TimesheetEntryView.
    """
    excluded_statuses = ["rejected", "on_hold", "archived"]
    # Include select_related for fields commonly needed when displaying these jobs
    return Job.objects.exclude(
        status__in=excluded_statuses
    ).select_related("client")

def get_nz_tz() -> timezone | ZoneInfo:
    """
    Gets the New Zealand timezone object using either zoneinfo or pytz.

    Returns:
        timezone | ZoneInfo: A timezone object for Pacific/Auckland,
        using ZoneInfo if available (Python 3.9+) or falling back to pytz
    """
    try:
        from zoneinfo import ZoneInfo
        nz_timezone = ZoneInfo('Pacific/Auckland')
    except ImportError:
        import pytz
        nz_timezone = pytz.timezone('Pacific/Auckland')
    return nz_timezone

def get_machine_id(path="/etc/machine-id"):
    """
    Reads the machine ID from the specified path.
    Defaults to /etc/machine-id for Linux systems.
    """
    try:
        with open(path) as f:
            return f.read().strip()
    except FileNotFoundError:
        logger.warning(f"Machine ID file not found at {path}. Cannot determine production environment based on machine ID.")
        return None
    except Exception as e:
        logger.error(f"Error reading machine ID file {path}: {e}")
        return None
    