"""Scheduled job functions for the job app."""

import logging
from datetime import datetime

from django.db import close_old_connections

from apps.workflow.services.error_persistence import persist_app_error

logger = logging.getLogger(__name__)


def set_paid_flag_jobs():
    """Set paid flag on completed jobs that have paid invoices."""
    logger.info(f"Running set_paid_flag_jobs at {datetime.now()}.")
    try:
        close_old_connections()

        # Import here to avoid Django startup issues
        from apps.job.services.paid_flag_service import PaidFlagService

        result = PaidFlagService.update_paid_flags(dry_run=False, verbose=True)

        logger.info(
            f"Successfully updated {result.jobs_updated} jobs as paid. "
            f"Jobs with unpaid invoices: {result.unpaid_invoices}. "
            f"Jobs without invoices: {result.missing_invoices}. "
            f"Operation completed in {result.duration_seconds:.2f} seconds."
        )
    except Exception as e:
        persist_app_error(e)
        logger.error(f"Error during set_paid_flag_jobs: {e}", exc_info=True)
