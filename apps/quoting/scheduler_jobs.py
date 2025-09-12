"""
Standalone job functions for APScheduler.
These functions must be independent to ensure they can be properly serialized.
"""

import logging

from django.core.management import call_command
from django.db import close_old_connections

logger = logging.getLogger(__name__)


def run_all_scrapers_job():
    """
    This job runs the Django management command to execute all scrapers.
    """
    logger.info("Attempting to run all scrapers via scheduled job.")
    try:
        close_old_connections()  # Close old DB connections to prevent issues
        call_command(
            "run_scrapers"
        )  # This calls the existing quoting/management/commands/run_scrapers.py
        logger.info("Successfully completed scheduled scraper run.")
    except Exception as e:
        logger.error(f"Error during scheduled scraper run: {e}", exc_info=True)


def delete_old_job_executions(max_age_days=7):
    """
    This job deletes entries from the DjangoJobExecution table that are older than `max_age_days`.
    It helps keep the table clean.
    """
    # Import here to avoid circular imports
    from django_apscheduler.models import DjangoJobExecution

    logger.info(f"Deleting old job executions older than {max_age_days} days.")
    DjangoJobExecution.objects.delete_old_job_executions(max_age_days)
