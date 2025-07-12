import logging

from django.apps import AppConfig

from apps.workflow.scheduler import get_scheduler

logger = logging.getLogger(__name__)


class JobConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.job"

    def ready(self) -> None:
        self._register_job_jobs()

    def _register_job_jobs(self) -> None:
        from apps.job.scheduler_jobs import set_paid_flag_jobs

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
