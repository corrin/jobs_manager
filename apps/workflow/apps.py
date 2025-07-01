import logging
import os
import sys

from django.apps import AppConfig
from django.conf import settings

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

    def ready(self):
        # This app (workflow) is responsible for scheduling Xero-related jobs.
        # The 'quoting' app handles its own scheduled jobs (e.g., scrapers).
        # Both apps use the same DjangoJobStore for persistence.

        # Prevent scheduler from running multiple times, especially during development
        # or when running management commands like runserver.
        # RUN_MAIN is set by Django in the main process.
        # ── guard #1: skip Django auto-reload child in DEBUG (already present)
        if settings.DEBUG and os.environ.get("RUN_MAIN") != "true":
            logger.info("Skipping APScheduler setup in debug child process.")
            return

        # ── guard #2: skip all ad-hoc manage.py commands ──────────────────
        if sys.argv[0].endswith("manage.py"):
            cmd = sys.argv[1] if len(sys.argv) > 1 else ""
            if cmd not in {"runserver"}:  # list any long-running cmds you *do* want
                logger.info(
                    "Skipping APScheduler setup inside manage.py %s", cmd or "<no-cmd>"
                )
                return

        # Only start the scheduler if it hasn't been started already
        # This check is crucial to prevent multiple scheduler instances in production.
        # Import scheduler-related modules here, when apps are ready
        # These imports are placed here to avoid AppRegistryNotReady errors
        # during Django management commands (like migrate) where the app registry
        # might not be fully loaded when apps.py is initially processed.
        from apscheduler.schedulers.background import BackgroundScheduler
        from django_apscheduler.jobstores import DjangoJobStore

        if not hasattr(self, "xero_scheduler_started"):
            self.xero_scheduler_started = True
            logger.info("Starting APScheduler for Xero-related jobs...")

            scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)
            scheduler.add_jobstore(DjangoJobStore(), "default")

            # Clear old jobs to prevent duplicates on restart
            scheduler.remove_all_jobs()

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
            logger.info("Added 'xero_heartbeat' job to scheduler.")

            # Xero Regular Sync: Perform full Xero synchronization weekly on Saturdays
            scheduler.add_job(
                xero_regular_sync_job,  # Use standalone function
                trigger="cron",
                day_of_week="sat",  # Saturday
                hour=1,  # 1 AM
                minute=0,
                timezone="Pacific/Auckland",  # Explicitly set NZT
                id="xero_regular_sync",
                max_instances=1,
                replace_existing=True,
                misfire_grace_time=60 * 60,  # 1 hour grace time
                coalesce=True,
            )
            logger.info("Added 'xero_regular_sync' job to scheduler.")

            # Xero 30-Day Sync: Perform full Xero synchronization on a Saturday morning every ~30 days
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
            logger.info("Added 'xero_30_day_sync' job to scheduler (Saturday morning).")

            try:
                scheduler.start()
                logger.info("APScheduler started successfully (for Xero related jobs).")
            except Exception as e:
                logger.error(
                    f"Error starting APScheduler for Xero jobs: {e}", exc_info=True
                )
