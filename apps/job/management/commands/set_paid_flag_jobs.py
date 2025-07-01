import logging

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.job.models import Job

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
        start_time = timezone.now()

        if dry_run:
            self.stdout.write(
                self.style.WARNING("Running in dry-run mode - no changes will be made")
            )

        completed_jobs = Job.objects.filter(status="completed", paid=False)

        if verbose:
            self.stdout.write(
                f"Found {completed_jobs.count()} completed jobs not marked as paid"
            )

        jobs_to_update = []
        unpaid_invoices = 0
        missing_invoices = 0

        for job in completed_jobs:
            try:
                invoice = job.invoice
                has_invoice = True
            except Job.invoice.RelatedObjectDoesNotExist:
                has_invoice = False

            if not has_invoice:
                missing_invoices += 1
                if verbose:
                    self.stdout.write(
                        f"Job {job.job_number} - {job.name} has no associate invoice"
                    )
                continue

            if not invoice.paid:
                unpaid_invoices += 1
                if verbose:
                    self.stdout.write(
                        f"Job {job.job_number} - {job.name} has unpaid invoice {job.invoice.number}"
                    )
            else:
                if verbose:
                    self.stdout.write(
                        f"Job {job.job_number} - {job.name} has paid invoice {job.invoice.number}"
                    )
                if dry_run:
                    (
                        self.stdout.write(
                            f"Would mark job {job.job_number} - {job.name} as paid"
                        )
                        if dry_run
                        else None
                    )

            jobs_to_update.append(job)

        if not dry_run and jobs_to_update:
            with transaction.atomic():
                for job in jobs_to_update:
                    job.paid = True
                    job.save(update_fields=["paid"])
                    logger.info(f"Job {job.job_number} ({job.name}) marked as paid")

        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()

        self.stdout.write(
            self.style.SUCCESS(
                f"{'Would update' if dry_run else 'Successfully updated'} "
                f"{len(jobs_to_update)} jobs as paid\n"
                f"Jobs with unpaid invoices: {unpaid_invoices}\n"
                f"Jobs without invoices: {missing_invoices}\n"
                f"Operation completed in {duration:.2f} seconds"
            )
        )
