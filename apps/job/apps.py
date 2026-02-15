import logging

from django.apps import AppConfig
from django.conf import settings

from apps.workflow.scheduler import get_scheduler

logger = logging.getLogger(__name__)


class JobConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.job"

    def ready(self) -> None:
        if settings.RUN_SCHEDULER:
            self._register_job_jobs()

    def _register_job_jobs(self) -> None:
        # Import here to avoid AppRegistryNotReady during Django startup
        from apps.job.scheduler_jobs import (
            auto_archive_completed_jobs,
            set_paid_flag_jobs,
        )

        scheduler = get_scheduler()

        # Set paid flag on completed jobs with paid invoices - nightly at 2 AM NZT
        scheduler.add_job(
            set_paid_flag_jobs,
            trigger="cron",
            hour=2,
            minute=0,
            timezone="Pacific/Auckland",
            id="set_paid_flag_jobs",
            max_instances=1,
            replace_existing=True,
            misfire_grace_time=60 * 60,  # 1 hour grace time
            coalesce=True,
        )
        logger.info("Added 'set_paid_flag_jobs' to shared scheduler.")

        # Auto-archive paid recently_completed jobs - nightly at 3 AM NZT
        # Runs after paid-flag job so freshly-paid jobs are eligible
        scheduler.add_job(
            auto_archive_completed_jobs,
            trigger="cron",
            hour=3,
            minute=0,
            timezone="Pacific/Auckland",
            id="auto_archive_completed_jobs",
            max_instances=1,
            replace_existing=True,
            misfire_grace_time=60 * 60,  # 1 hour grace time
            coalesce=True,
        )
        logger.info("Added 'auto_archive_completed_jobs' to shared scheduler.")
