"""Utility functions for job-related operations."""

from django.db import models

from apps.job.models import Job


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


def get_active_jobs() -> models.QuerySet[Job]:
    """
    Returns a queryset of Jobs considered active for work or resource assignment
    (e.g., time entry, stock allocation).

    Excludes jobs that are rejected, on hold, completed, or archived.
    This matches the filter used in the TimesheetEntryView.
    """
    excluded_statuses = ["rejected", "on_hold", "archived"]
    # Include select_related for fields commonly needed when displaying these jobs
    return Job.objects.exclude(status__in=excluded_statuses).select_related("client")
