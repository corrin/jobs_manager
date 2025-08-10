#!/usr/bin/env python
"""
Test actual job sync - no synthetic data.
The purpose of this script is to help us write sync_job_to_xero
Therefore it cannot ever call sync_job_to_xero, as that would be circular

"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jobs_manager.settings')
django.setup()

from apps.job.models.job import Job
from apps.workflow.api.xero.xero import create_project
from apps.workflow.api.xero.sync import get_or_fetch_client
from django.utils import timezone
from datetime import datetime

def main():
    # Get a real job with real data
    job = Job.objects.filter(client__xero_contact_id__isnull=False).first()
    print(f"Testing job: {job.name}")
    print(f"Client: {job.client.name}")
    contact_id = job.client.xero_contact_id
    print(f"Contact ID: {contact_id}")

    # Inline sync logic to debug step by step
    print(f"Syncing Job {job.job_number} ({job.name}) to Xero")

    # Validation - defensive programming
    if not job.client:
        raise ValueError(f"Job {job.job_number} has no client")

    if not job.client.xero_contact_id:
        raise ValueError(f"Job {job.job_number} client '{job.client.name}' has no xero_contact_id")

    # Validate contact exists in Xero - fail early
    valid_client = get_or_fetch_client(job.client.xero_contact_id, f"job {job.job_number}")
    print(f"✅ Validated client exists in Xero: {valid_client.name}")
    print(f"Client object dump:")
    print(vars(valid_client))

    # Prepare project data
    project_data = {
        "name": job.name,
        "contact_id": job.client.xero_contact_id,
    }

    # Add optional fields - defensive programming
    if not job.delivery_date:
        # Skip deadline - it's optional in Xero
        pass
    else:
        # Convert date to timezone-aware datetime at end of day
        delivery_datetime = timezone.make_aware(
            datetime.combine(job.delivery_date, datetime.max.time())
        )
        project_data["deadline_utc"] = delivery_datetime

    # Handle estimate - defensive programming
    if not job.latest_estimate:
        raise ValueError(f"Job {job.job_number} has no latest_estimate")

    estimate_total = job.latest_estimate.total_revenue
    project_data["estimate_amount"] = float(estimate_total)

    print(f"Project data: {project_data}")

    # Create project
    print(f"Creating new Xero project for Job {job.job_number}")
    response = create_project(project_data)
    print(f"Xero response: {response}")
    # Save the project ID back to our job
    job.xero_project_id = response.project_id
    job.xero_last_synced = timezone.now()
    job.save(update_fields=['xero_project_id', 'xero_last_synced'])

    print(f"✅ SUCCESS: Created Job {job.job_number} in Xero with project ID {job.xero_project_id}")

if __name__ == "__main__":
    main()
