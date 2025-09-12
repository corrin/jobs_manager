"""
Standalone job functions for APScheduler related to Xero synchronization.
These functions must be independent to ensure they can be properly serialized.
"""

import logging
from datetime import datetime

from django.db import close_old_connections

logger = logging.getLogger(__name__)
scheduler_logger = logging.getLogger("django_apscheduler")


def xero_heartbeat_job() -> None:
    """
    Refreshes the Xero API token.
    """
    scheduler_logger.info(f"Attempting Xero Heartbeat job at {datetime.now()}.")
    try:
        close_old_connections()
        # Import models/services here to avoid AppRegistryNotReady errors during Django startup
        from apps.workflow.api.xero.xero import refresh_token

        result = refresh_token()
        if result:
            scheduler_logger.info("Xero API token refreshed successfully.")
        else:
            scheduler_logger.error("Error: No Xero token available to refresh.")
    except Exception as e:
        scheduler_logger.error(f"Error during Xero Heartbeat job: {e}", exc_info=True)


def xero_regular_sync_job() -> None:
    """
    Performs a full Xero synchronization.
    """
    logger.info(f"Running Xero Regular Sync job at {datetime.now()}.")
    try:
        close_old_connections()
        # Import models/services here to avoid AppRegistryNotReady errors during Django startup
        from apps.workflow.services.xero_sync_service import XeroSyncService

        XeroSyncService.start_sync()
        logger.info("Xero regular sync completed successfully.")
    except Exception as e:
        logger.error(f"Error during Xero Regular Sync job: {e}", exc_info=True)


def xero_30_day_sync_job() -> None:
    """
    Performs a full Xero synchronization for the 30-day sync.
    """
    logger.info(f"Running Xero 30-Day Sync job at {datetime.now()}.")
    try:
        close_old_connections()
        # Import models/services here to avoid AppRegistryNotReady errors during Django startup
        from apps.workflow.services.xero_sync_service import XeroSyncService

        XeroSyncService.start_sync()
        logger.info("Xero 30-day sync completed successfully.")
    except Exception as e:
        logger.error(f"Error during Xero 30-Day Sync job: {e}", exc_info=True)
