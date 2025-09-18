"""
Shared APScheduler instance for the entire Django application.

This module provides a single scheduler instance that can be used by all Django apps
to avoid conflicts between multiple scheduler instances. The scheduler is created
once at import time and can be started/stopped as needed.
"""

import logging
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from django.conf import settings

logger = logging.getLogger(__name__)

# Single scheduler instance - created once at import time
scheduler: Optional[BackgroundScheduler] = None


def get_scheduler() -> BackgroundScheduler:
    """Get the shared scheduler instance, creating it if necessary."""
    global scheduler
    if scheduler is None:
        logger.info("Creating shared APScheduler instance")
        scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)

        # Import here to avoid circular import during Django startup
        from django_apscheduler.jobstores import DjangoJobStore

        scheduler.add_jobstore(DjangoJobStore(), "default")
    return scheduler


def stop_scheduler() -> bool:
    """
    Stop the scheduler if it's running.

    Returns:
        bool: True if scheduler was stopped, False if it wasn't running
    """
    scheduler_instance = get_scheduler()
    if scheduler_instance.running:
        try:
            scheduler_instance.shutdown()
            logger.info("Shared APScheduler stopped successfully")
            return True
        except Exception as e:
            logger.error(f"Error stopping shared APScheduler: {e}", exc_info=True)
            return False
    return False
