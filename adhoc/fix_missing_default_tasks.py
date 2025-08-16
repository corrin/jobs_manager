#!/usr/bin/env python
"""
One-off script to create default tasks for existing jobs with Xero projects
but no xero_default_task_id (dev environment only)
"""

import logging
import os
import time

import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jobs_manager.settings")
django.setup()

from apps.job.models.job import Job
from apps.workflow.api.xero.xero import create_default_task

logger = logging.getLogger(__name__)
SLEEP_TIME = 1


def main():
    # Find jobs with Xero projects but no default task ID
    jobs_needing_tasks = Job.objects.filter(
        xero_project_id__isnull=False, xero_default_task_id__isnull=True
    )

    logger.info(f"Found {jobs_needing_tasks.count()} jobs needing default tasks")

    for job in jobs_needing_tasks:
        try:
            logger.info(f"Creating default task for Job {job.job_number} ({job.name})")
            logger.info(f"  Xero project ID: {job.xero_project_id}")

            # Create default task
            default_task = create_default_task(job.xero_project_id)
            time.sleep(SLEEP_TIME)

            # Update job with task ID
            job.xero_default_task_id = default_task.task_id
            job.save(update_fields=["xero_default_task_id"])

            logger.info(f"  Created default task ID: {job.xero_default_task_id}")

        except Exception as e:
            logger.error(f"Failed to create default task for Job {job.job_number}: {e}")
            raise  # FAIL EARLY

    logger.info("Completed creating default tasks for existing jobs")


if __name__ == "__main__":
    main()
