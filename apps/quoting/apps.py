import logging
import os
import sys

from django.apps import AppConfig
from django.conf import settings

logger = logging.getLogger(__name__)


class QuotingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.quoting"

    def ready(self):
        # Import signals to ensure they're connected
        # This app (quoting) is responsible for scheduling scraper jobs.
        # The 'workflow' app handles its own scheduled jobs (e.g., Xero syncs).
        # Both apps use the same DjangoJobStore for persistence.
        # Import scheduler-related modules here, when apps are ready
        # These imports are placed here to avoid AppRegistryNotReady errors
        # during Django management commands (like migrate) where the app registry
        # might not be fully loaded when apps.py is initially processed.
        from apscheduler.schedulers.background import BackgroundScheduler
        from django_apscheduler.jobstores import DjangoJobStore

        import apps.quoting.signals  # noqa

        # Skip scheduler in one-off manage.py commands (migrate, shell, etc.)
        if sys.argv[0].endswith("manage.py"):
            cmd = sys.argv[1] if len(sys.argv) > 1 else ""
            if cmd != "runserver":  # runserver still needs the scheduler
                logger.info(
                    "Skipping APScheduler setup inside manage.py %s", cmd or "<no-cmd>"
                )
                return

        # Import the standalone job functions
        from apps.quoting.scheduler_jobs import (
            delete_old_job_executions,
            run_all_scrapers_job,
        )

        # Ensure Django is ready before starting the scheduler
        # This check prevents the scheduler from starting multiple times
        # or before the Django app registry is fully populated.
        if settings.DEBUG and os.environ.get("RUN_MAIN") != "true":
            # In debug mode, Django's runserver often reloads code,
            # causing ready() to be called multiple times.
            # RUN_MAIN is a flag set by Django to indicate the main process.
            # We only want to run the scheduler in the main process.
            logger.info("Skipping scraper scheduler setup in debug child process.")
            return

        # Only start the scheduler if it hasn't been started already
        # This is a simple check to prevent multiple scheduler instances
        # in production environments where ready() might still be called more than once.
        if not hasattr(self, "scraper_scheduler_started"):
            self.scraper_scheduler_started = True
            logger.info("Starting APScheduler for scraper jobs...")

            scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)
            scheduler.add_jobstore(DjangoJobStore(), "default")

            # Clear old jobs to prevent duplicates on restart
            scheduler.remove_all_jobs()

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
            logger.info("Added 'run_all_scrapers_weekly' job to scheduler.")

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
            logger.info("Added 'delete_old_job_executions' job to scheduler.")

            try:
                scheduler.start()
                logger.info("APScheduler started successfully for scraper jobs.")
            except Exception as e:
                logger.error(
                    f"Error starting APScheduler for scraper jobs: {e}", exc_info=True
                )
