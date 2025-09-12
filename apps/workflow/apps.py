import logging

from django.apps import AppConfig
from django.conf import settings

from apps.workflow.scheduler import get_scheduler

# Import standalone job functions
from apps.workflow.scheduler_jobs import (
    xero_30_day_sync_job,
    xero_heartbeat_job,
    xero_regular_sync_job,
)

logger = logging.getLogger(__name__)


class WorkflowConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.workflow"
    verbose_name = "Workflow"

    def ready(self) -> None:
        # This app (workflow) is responsible for scheduling Xero-related jobs.
        # The 'quoting' app handles its own scheduled jobs (e.g., scrapers).
        # Both apps use the same shared scheduler instance for job management.

        # Register Xero jobs with the shared scheduler
        if settings.RUN_SCHEDULER:
            self._register_xero_jobs()

    def _register_xero_jobs(self) -> None:
        """Register Xero-related jobs with the shared scheduler."""
        scheduler = get_scheduler()

        # Xero Heartbeat: Refresh Xero API token every 5 minutes
        scheduler.add_job(
            xero_heartbeat_job,  # Use standalone function
            trigger="interval",
            minutes=5,
            id="xero_heartbeat",
            max_instances=1,
            replace_existing=True,
            misfire_grace_time=60,  # 1 minute grace time
            coalesce=True,
        )
        logger.info("Added 'xero_heartbeat' job to shared scheduler.")

        # Xero Regular Sync: Perform full Xero synchronization hourly
        scheduler.add_job(
            xero_regular_sync_job,  # Use standalone function
            trigger="interval",
            hours=1,
            id="xero_regular_sync",
            max_instances=1,
            replace_existing=True,
            misfire_grace_time=60 * 60,  # 1 hour grace time
            coalesce=True,
        )
        logger.info("Added 'xero_regular_sync' job to shared scheduler.")

        # Xero 30-Day Sync: Perform full Xero synchronization on Saturday morning
        # every ~30 days
        scheduler.add_job(
            xero_30_day_sync_job,  # Use standalone function
            trigger="cron",
            day_of_week="sat",  # Saturday
            hour=2,  # 2 AM
            minute=0,
            timezone="Pacific/Auckland",  # Explicitly set NZT
            id="xero_30_day_sync",
            max_instances=1,
            replace_existing=True,
            misfire_grace_time=24 * 60 * 60,  # 24 hour grace time
            coalesce=True,
        )
        logger.info(
            "Added 'xero_30_day_sync' job to shared scheduler (Saturday morning)."
        )
