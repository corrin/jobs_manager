"""
Shared APScheduler instance for the entire Django application.

This module provides a single scheduler instance that can be used by all Django apps
to avoid conflicts between multiple scheduler instances. The scheduler is created
once at import time and can be started/stopped as needed.
"""

import logging
import os
import sys
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


def should_start_scheduler() -> bool:
    """
    Determine if the scheduler should be started in the current context.

    Returns False if:
    - Running under Django's autoreloader (development)
    - Running a management command other than runserver
    - Already running

    Returns True if:
    - Running in production
    - Running the runserver command
    """
    # Skip if running under Django's autoreloader in development
    # Check for RUN_MAIN environment variable which Django sets in the main process
    if settings.DEBUG and os.environ.get("RUN_MAIN") != "true":
        logger.info(
            "Skipping scheduler startup - running in Django autoreloader child process"
        )
        return False

    # Skip if running management commands other than runserver
    if sys.argv[0].endswith("manage.py"):
        cmd = sys.argv[1] if len(sys.argv) > 1 else ""
        if cmd not in {"runserver", "runserver_with_ngrok"}:
            logger.info(
                f"Skipping scheduler startup - running management command: {cmd}"
            )
            return False

    # Skip if scheduler is already running
    scheduler_instance = get_scheduler()
    if scheduler_instance.running:
        logger.info("Scheduler already running")
        return False

    return True


def start_scheduler() -> bool:
    """
    Start the scheduler if appropriate conditions are met.

    Returns:
        bool: True if scheduler was started, False if it was already running or shouldn't start
    """
    if not should_start_scheduler():
        return False

    try:
        scheduler_instance = get_scheduler()
        scheduler_instance.start()
        logger.info("Shared APScheduler started successfully")
        return True
    except Exception as e:
        logger.error(f"Error starting shared APScheduler: {e}", exc_info=True)
        return False


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
