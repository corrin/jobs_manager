from django.core.management.base import BaseCommand
from django.db.models import Q

from apps.job.enums import JobPricingStage
from apps.job.models import Job, JobPricing


class Command(BaseCommand):
    help = "Validates jobs for missing required fields and invalid data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--delete",
            action="store_true",
            help="Delete invalid records after confirmation",
        )

    def handle(self, *args, **options):
        self.stdout.write("Starting job validation...\n")

        # 1. Check for jobs missing required fields
        invalid_jobs = Job.objects.filter(
            Q(name__isnull=True)
            | Q(name="")
            | Q(job_number__isnull=True)
            | Q(client__isnull=True)
        )

        if invalid_jobs.exists():
            self.stdout.write(self.style.ERROR("\nJobs missing required fields:"))
            for job in invalid_jobs:
                missing_fields = []
                if not job.name:
                    missing_fields.append("name")
                if not job.job_number:
                    missing_fields.append("job_number")
                if not job.client:
                    missing_fields.append("client")

                self.stdout.write(
                    self.style.ERROR(
                        f"Job ID: {job.id} - Missing fields: {', '.join(missing_fields)}"
                    )
                )
        else:
            self.stdout.write(self.style.SUCCESS("All jobs have required fields ✓"))

        # 2. Check for reality pricing with no timesheets
        reality_pricing_without_time = JobPricing.objects.filter(
            pricing_stage=JobPricingStage.REALITY, time_entries__isnull=True
        ).select_related("job")

        if reality_pricing_without_time.exists():
            self.stdout.write(self.style.ERROR("\nReality pricing with no timesheets:"))
            for pricing in reality_pricing_without_time:
                self.stdout.write(
                    self.style.ERROR(
                        f"Job ID: {pricing.job.id} - Job Name: {pricing.job.name} - "
                        f"Job Number: {pricing.job.job_number}"
                    )
                )
        else:
            self.stdout.write(
                self.style.SUCCESS("All reality pricing has associated timesheets ✓")
            )

        # Summary
        total_jobs = Job.objects.count()
        total_invalid = invalid_jobs.count()
        total_no_timesheet = reality_pricing_without_time.count()

        self.stdout.write("\nSummary:")
        self.stdout.write(f"Total jobs checked: {total_jobs}")
        self.stdout.write(f"Jobs with missing required fields: {total_invalid}")
        self.stdout.write(f"Reality pricing without timesheets: {total_no_timesheet}")

        # Handle deletion if requested
        if options["delete"] and (total_invalid > 0 or total_no_timesheet > 0):
            self.stdout.write("\nDeletion Summary:")
            self.stdout.write(
                f"- {total_invalid} jobs with missing required fields will be deleted"
            )
            self.stdout.write(
                f"- {total_no_timesheet} reality pricing entries without timesheets will be deleted"
            )

            confirm = input("\nAre you sure you want to delete these records? [y/N]: ")

            if confirm.lower() == "y":
                deleted_jobs = 0
                deleted_pricing = 0

                if total_invalid > 0:
                    deleted_jobs = invalid_jobs.delete()[0]
                if total_no_timesheet > 0:
                    deleted_pricing = reality_pricing_without_time.delete()[0]

                self.stdout.write(
                    self.style.SUCCESS(
                        f"\nSuccessfully deleted {deleted_jobs} jobs and {deleted_pricing} reality pricing entries"
                    )
                )
            else:
                self.stdout.write("\nDeletion cancelled")
