import logging

from django.core.management.base import BaseCommand

from apps.job.services.paid_flag_service import PaidFlagService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sets the "paid" flag on completed jobs that have paid invoices'

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without making any changes",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Display detailed information about processed jobs",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        verbose = options["verbose"]

        if dry_run:
            self.stdout.write(
                self.style.WARNING("Running in dry-run mode - no changes will be made")
            )

        # Use the shared service
        result = PaidFlagService.update_paid_flags(dry_run=dry_run, verbose=verbose)

        # Output verbose info to stdout for management command
        if verbose:
            for job in result.processed_jobs:
                if dry_run:
                    self.stdout.write(f"Would mark job {job.job_number} - {job.name} as paid")
                else:
                    self.stdout.write(f"Marked job {job.job_number} - {job.name} as paid")

        self.stdout.write(
            self.style.SUCCESS(
                f"{'Would update' if dry_run else 'Successfully updated'} "
                f"{result.jobs_updated} jobs as paid\n"
                f"Jobs with unpaid invoices: {result.unpaid_invoices}\n"
                f"Jobs without invoices: {result.missing_invoices}\n"
                f"Operation completed in {result.duration_seconds:.2f} seconds"
            )
        )
