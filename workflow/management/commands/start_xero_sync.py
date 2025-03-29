from django.core.management.base import BaseCommand
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from django.utils import timezone
from django.core.cache import cache
import logging
import os

from workflow.models.xero_token import XeroToken
from workflow.api.xero.sync import synchronise_xero_data
from workflow.api.xero.xero import get_valid_token, refresh_token

logger = logging.getLogger("xero")

class Command(BaseCommand):
    help = 'Starts the Xero sync scheduler with token refresh heartbeat'

    def handle(self, *args, **options):
        # Add a console handler directly to our logger
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        
        # Get our logger and add the handler
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        
        # Test that debug logging is working
        logger.debug("Debug logging enabled for Xero sync process")

        def token_heartbeat():
            """Refresh Xero token every 5 minutes."""
            try:
                token = XeroToken.objects.first()
                if not token:
                    logger.debug("No Xero token found. Skipping refresh.")
                    return
                
                logger.debug("Running token heartbeat - refreshing Xero token")
                refresh_token()
                logger.debug("Token heartbeat completed")
            except Exception as e:
                logger.error(f"Error in token refresh: {str(e)}")

        def xero_sync_job():
            """Full data sync job that runs hourly."""
            # Check if we have a valid Xero token
            token = XeroToken.objects.first()
            if not token:
                logger.info("No Xero token found. Skipping sync.")
                return
            
            logger.info(f"Starting scheduled Xero sync at {timezone.now()}")
            # Consume the generator to execute the sync process
            for message in synchronise_xero_data():
                entity = message.get('entity', 'unknown')
                msg = message.get('message', '')
                severity = message.get('severity', 'info')
                
                # Log important messages
                if severity in ['error', 'warning'] or 'Starting' in msg or 'Completed' in msg:
                    logger.info(f"[{severity.upper()}] {entity}: {msg}")
            
            logger.info(f"Completed scheduled Xero sync at {timezone.now()}")

        # Get sync interval from environment variable (default to 1 hour)
        sync_interval_hours = int(os.getenv('XERO_SYNC_INTERVAL_HOURS', '1'))
        logger.info(f"Configuring Xero sync to run every {sync_interval_hours} hour(s)")

        # Initialize the scheduler
        scheduler = BackgroundScheduler()

        # Add the token heartbeat job - runs every 5 minutes
        scheduler.add_job(
            token_heartbeat,
            trigger=IntervalTrigger(minutes=5),
            id='xero_token_heartbeat',
            name='Xero Token Heartbeat',
            replace_existing=True,
            next_run_time=timezone.now()  # Run immediately on startup
        )

        # Add the full sync job
        scheduler.add_job(
            xero_sync_job,
            trigger=IntervalTrigger(hours=sync_interval_hours),
            id='xero_sync_job',
            name='Xero Sync Job',
            replace_existing=True,
            next_run_time=timezone.now()  # Run immediately on startup
        )

        # Start the scheduler
        scheduler.start()
        logger.info("Started Xero scheduler with token heartbeat")

        try:
            # Keep the script running
            while True:
                pass
        except (KeyboardInterrupt, SystemExit):
            scheduler.shutdown()
            