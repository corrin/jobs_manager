import uuid
from django.contrib.messages import get_messages


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


def get_excluded_staff():
    """
    Retrieves the IDs of staff members who are excluded from the scheduling system.

    Returns:
        list: A list of staff IDs (as strings) who are excluded from the scheduling system
    """
    # Static list of excluded staff IDs
    static_excluded_ids = [
        "a9bd99fa-c9fb-43e3-8b25-578c35b56fa6",
        "b50dd08a-58ce-4a6c-b41e-c3b71ed1d402",
        "d335acd4-800e-517a-8ff4-ba7aada58d14",
        "e61e2723-26e1-5d5a-bd42-bbd318ddef81",
    ]
    
    # Delaying database query execution
    from django.apps import apps
    from django.db.utils import ProgrammingError, OperationalError
    
    if apps.ready:
        try:
            # Get the Staff model dynamically only when needed
            # This is so the installation process can run without the database being ready
            from workflow.models import Staff
            dynamic_excluded_ids = [
                str(staff.id) for staff in Staff.objects.filter(ims_payroll_id__isnull=True)
            ]
            return static_excluded_ids + dynamic_excluded_ids
        except (ProgrammingError, OperationalError):
            # If the table doesn't exist yet (during migrations), return only static IDs
            return static_excluded_ids
    
    # Return only static IDs if apps are not ready
    return static_excluded_ids
