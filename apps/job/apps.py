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

    def configure_gemini_api(self) -> None:
        """
        Configure Gemini API once at Django startup.

        This ensures the API is ready for file uploads and chat requests
        without needing to reconfigure on every request.

        TODO: This accesses the database during app initialization which Django
        discourages. Consider lazy initialization or environment variable config.
        """
        try:
            # Import here to avoid AppRegistryNotReady during Django startup
            import google.generativeai as genai

            from apps.workflow.enums import AIProviderTypes
            from apps.workflow.models import AIProvider

            ai_provider = AIProvider.objects.filter(
                provider_type=AIProviderTypes.GOOGLE
            ).first()

            if ai_provider and ai_provider.api_key:
                genai.configure(api_key=ai_provider.api_key)
                logger.info("Gemini API configured successfully at startup")
            else:
                logger.warning(
                    "No Gemini AI provider found - chat features may not work"
                )
        except Exception as e:
            logger.error(f"Failed to configure Gemini API at startup: {e}")
