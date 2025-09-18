from django.core.management.base import BaseCommand

from apps.workflow.scheduler import get_scheduler


class Command(BaseCommand):
    help = "Start the shared APScheduler loop (runs forever)."

    def handle(self, *args, **options):
        import signal
        import sys

        try:
            scheduler = get_scheduler()
            scheduler.start()
            self.stdout.write(
                self.style.SUCCESS("APScheduler started. Waiting for jobs…")
            )
            signal.pause()  # keep the process alive until SIGTERM/SIGINT
        except Exception as e:
            self.stderr.write(f"Failed to start scheduler: {e}")
            sys.exit(1)
