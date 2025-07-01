from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.job.enums import JobPricingMethodology
from apps.job.models import AdjustmentEntry, Job


def get_accounting_date_for_job(job):
    """Get the appropriate accounting date for a job's quote adjustment"""
    # Try invoice date first
    if hasattr(job, "invoice") and job.invoice:
        return job.invoice.date

    # Fall back to latest date from entries
    latest_dates = []

    # Time entries
    for entry in job.latest_reality_pricing.time_entries.all():
        if entry.date:
            latest_dates.append(entry.date)
        else:
            print(
                f"WARNING: Job {job.job_number} has time entry {entry.id} with no date"
            )

    # Material entries
    for entry in job.latest_reality_pricing.material_entries.all():
        if entry.accounting_date:
            latest_dates.append(entry.accounting_date)
        else:
            print(
                f"WARNING: Job {job.job_number} has material entry {entry.id} with no accounting_date"
            )

    # Adjustment entries (excluding quote adjustments)
    for entry in job.latest_reality_pricing.adjustment_entries.filter(
        is_quote_adjustment=False
    ):
        if entry.accounting_date:
            latest_dates.append(entry.accounting_date)
        else:
            print(
                f"WARNING: Job {job.job_number} has adjustment entry {entry.id} with no accounting_date"
            )

    if latest_dates:
        return max(latest_dates)

    # Last resort fallback to today
    return timezone.now().date()


class Command(BaseCommand):
    help = "Backfill quote adjustments for completed/archived fixed-price jobs"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without making changes",
        )
        parser.add_argument(
            "--reprocess",
            action="store_true",
            help="Recalculate existing quote adjustments",
        )

    def handle(self, **options):
        dry_run = options["dry_run"]
        reprocess = options["reprocess"]

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No changes will be made")
            )

        if reprocess:
            # Find all existing quote adjustments
            existing_adjustments = AdjustmentEntry.objects.filter(
                is_quote_adjustment=True
            ).select_related("job_pricing__job__latest_quote_pricing")

            self.stdout.write(
                f"Found {existing_adjustments.count()} existing quote adjustments"
            )

            updated_count = 0

            for adjustment in existing_adjustments:
                job = adjustment.job_pricing.job

                # Calculate what the adjustment should be
                quote_revenue = Decimal(str(job.latest_quote_pricing.total_revenue))

                # Calculate reality revenue excluding this quote adjustment
                reality_revenue = Decimal(str(job.latest_reality_pricing.total_revenue))
                reality_revenue -= adjustment.price_adjustment

                correct_adjustment = quote_revenue - reality_revenue

                # Get correct accounting date
                correct_date = get_accounting_date_for_job(job)

                # Check if update is needed
                needs_update = (
                    abs(adjustment.price_adjustment - correct_adjustment)
                    >= Decimal("0.01")
                    or adjustment.accounting_date != correct_date
                )

                if needs_update:
                    if dry_run:
                        self.stdout.write(
                            f"Job {job.job_number}: Would update adjustment from ${adjustment.price_adjustment} to ${correct_adjustment}, date from {adjustment.accounting_date} to {correct_date}"
                        )
                    else:
                        with transaction.atomic():
                            adjustment.price_adjustment = correct_adjustment
                            adjustment.accounting_date = correct_date
                            adjustment.comments = f"Recalculated adjustment. Quote: ${quote_revenue}, Reality: ${reality_revenue}"
                            adjustment.save()

                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Job {job.job_number}: Updated adjustment to ${correct_adjustment}"
                            )
                        )
                    updated_count += 1
                else:
                    self.stdout.write(f"Job {job.job_number}: No update needed")

            # Summary
            action = "Would update" if dry_run else "Updated"
            self.stdout.write(
                self.style.SUCCESS(
                    f"\\nSummary: {action} {updated_count} quote adjustments"
                )
            )
            return

        # Find completed or archived fixed-price jobs
        target_jobs = Job.objects.filter(
            status__in=["completed", "archived"],
            pricing_methodology=JobPricingMethodology.FIXED_PRICE,
        ).select_related("latest_quote_pricing", "latest_reality_pricing")

        self.stdout.write(
            f"Found {target_jobs.count()} completed/archived fixed-price jobs"
        )

        created_count = 0
        skipped_count = 0

        for job in target_jobs:
            # Check if quote adjustment already exists
            existing_adjustment = AdjustmentEntry.objects.filter(
                job_pricing=job.latest_reality_pricing, is_quote_adjustment=True
            ).exists()

            if existing_adjustment:
                self.stdout.write(
                    f"Job {job.job_number}: Quote adjustment already exists - skipping"
                )
                skipped_count += 1
                continue

            # Get quote and reality revenues
            quote_revenue = Decimal(str(job.latest_quote_pricing.total_revenue))
            reality_revenue = Decimal(str(job.latest_reality_pricing.total_revenue))

            # Exclude existing quote adjustments from reality revenue
            existing_quote_adjustments = (
                job.latest_reality_pricing.adjustment_entries.filter(
                    is_quote_adjustment=True
                )
            )
            for existing_adj in existing_quote_adjustments:
                reality_revenue -= existing_adj.price_adjustment

            # Calculate adjustment needed
            adjustment_amount = quote_revenue - reality_revenue

            # Only create if there's a difference
            if abs(adjustment_amount) < Decimal("0.01"):
                self.stdout.write(
                    f"Job {job.job_number}: No adjustment needed (quote={quote_revenue}, reality={reality_revenue})"
                )
                skipped_count += 1
                continue

            # Get accounting date
            accounting_date = get_accounting_date_for_job(job)

            if dry_run:
                self.stdout.write(
                    f"Job {job.job_number}: Would create ${adjustment_amount} adjustment on {accounting_date}"
                )
                created_count += 1
            else:
                # Create the adjustment entry
                with transaction.atomic():
                    AdjustmentEntry.objects.create(
                        job_pricing=job.latest_reality_pricing,
                        description="Adjusted to match quote",
                        price_adjustment=adjustment_amount,
                        cost_adjustment=Decimal("0.00"),
                        accounting_date=accounting_date,
                        comments=f"Backfilled adjustment. Quote: ${quote_revenue}, Reality: ${reality_revenue}",
                        is_quote_adjustment=True,
                    )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Job {job.job_number}: Created adjustment of ${adjustment_amount}"
                    )
                )
                created_count += 1

        # Summary
        action = "Would create" if dry_run else "Created"
        self.stdout.write(
            self.style.SUCCESS(
                f"\nSummary: {action} {created_count} quote adjustments, skipped {skipped_count} jobs"
            )
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "Run without --dry-run to actually create the adjustments"
                )
            )
