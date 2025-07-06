import os

from django.core.management.base import BaseCommand

from apps.workflow.scheduler import start_scheduler


class Command(BaseCommand):
    help = "Start the shared APScheduler loop (runs forever)."

    def handle(self, *args, **options):
        import signal
        import sys

        # instruct scheduler.py that we really want it to run
        os.environ["DJANGO_RUN_SCHEDULER"] = "1"

        if not start_scheduler(force=True):
            self.stderr.write("Scheduler already running or failed to start.")
            sys.exit(1)

        self.stdout.write(self.style.SUCCESS("APScheduler started. Waiting for jobs…"))
        signal.pause()  # keep the process alive until SIGTERM/SIGINT
