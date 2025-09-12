#!/usr/bin/env python
"""
Test CostLine sync functionality - force sync to test implementation
"""

import logging
import os

import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jobs_manager.settings")
django.setup()

from apps.job.models.job import Job
from apps.workflow.api.xero.sync import sync_job_to_xero

logger = logging.getLogger(__name__)


def main():
    # Find a job with xero_project_id and actual CostLines
    job = (
        Job.objects.filter(
            xero_project_id__isnull=False,
            cost_sets__kind="actual",
            cost_sets__cost_lines__isnull=False,
        )
        .distinct()
        .first()
    )

    if not job:
        logger.error("No job found with xero_project_id and actual CostLines")
        return

    logger.info(f"Testing sync for Job {job.job_number} ({job.name})")

    # Get CostLines and force sync by clearing timestamps
    actual_cost_sets = job.cost_sets.filter(kind="actual")
    for cost_set in actual_cost_sets:
        costlines = cost_set.cost_lines.all()
        logger.info(f"Found {costlines.count()} CostLines in actual cost set")

        for cl in costlines:
            # Clear sync timestamp to force sync
            cl.xero_last_synced = None
            cl.save(update_fields=["xero_last_synced"])
            logger.debug(f"Cleared sync timestamp for {cl.kind} CostLine: {cl.desc}")

    # Test the full job sync
    try:
        result = sync_job_to_xero(job)
        logger.info(f"Job sync result: {result}")

        # Check results
        for cost_set in actual_cost_sets:
            costlines = cost_set.cost_lines.all()
            for cl in costlines:
                cl.refresh_from_db()
                if cl.kind == "time":
                    logger.info(
                        f"Time CostLine {cl.id}: xero_time_id={cl.xero_time_id}"
                    )
                else:
                    logger.info(
                        f"Expense CostLine {cl.id}: xero_expense_id={cl.xero_expense_id}"
                    )

    except Exception as e:
        logger.error(f"Job sync failed: {e}", exc_info=True)


if __name__ == "__main__":
    main()
