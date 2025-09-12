import logging

from django.apps import AppConfig
from django.conf import settings

from apps.workflow.scheduler import get_scheduler

logger = logging.getLogger(__name__)


class QuotingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.quoting"

    def ready(self) -> None:
        # Signals removed - app uses explicit function calls instead

        # This app (quoting) is responsible for scheduling scraper jobs.
        # The 'workflow' app handles its own scheduled jobs (e.g., Xero syncs).
        # Both apps use the same shared scheduler instance for job management.
        # Register scraper jobs with the shared scheduler
        if settings.RUN_SCHEDULER:
            self._register_scraper_jobs()

    def _register_scraper_jobs(self) -> None:
        """Register scraper-related jobs with the shared scheduler."""
        # Import the standalone job functions
        from apps.quoting.scheduler_jobs import (
            delete_old_job_executions,
            run_all_scrapers_job,
        )

        scheduler = get_scheduler()

        # Schedule the scraper job to run every Sunday at 3 PM NZT
        scheduler.add_job(
            run_all_scrapers_job,  # Now using standalone function
            trigger="cron",
            day_of_week="sun",
            hour=15,  # 3 PM
            minute=0,
            id="run_all_scrapers_weekly",
            max_instances=1,
            replace_existing=True,
            misfire_grace_time=60 * 60,  # 1 hour grace time for missed runs
            coalesce=True,  # Only run once if multiple triggers fire
        )
        logger.info("Added 'run_all_scrapers_weekly' job to shared scheduler.")

        # Add a job to clean up old job executions
        scheduler.add_job(
            delete_old_job_executions,  # Now using standalone function
            trigger="interval",
            days=1,
            id="delete_old_job_executions",
            max_instances=1,
            replace_existing=True,
            misfire_grace_time=60 * 60,
            coalesce=True,
        )
        logger.info("Added 'delete_old_job_executions' job to shared scheduler.")
