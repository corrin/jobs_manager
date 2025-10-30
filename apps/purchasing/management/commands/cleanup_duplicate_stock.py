from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.purchasing.stock_cleanup import consolidate_duplicate_stock


class Command(BaseCommand):
    help = "Merge duplicate stock entries created from the same purchase order line."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Log planned changes without persisting updates.",
        )

    def handle(self, *args, **options):
        dry_run: bool = options.get("dry_run", False)

        if dry_run:
            self.stdout.write(self.style.WARNING("Running in dry-run mode."))

        summary = consolidate_duplicate_stock(dry_run=dry_run)

        status = "DRY RUN" if dry_run else "APPLIED"
        self.stdout.write(
            self.style.SUCCESS(
                f"[{status}] Groups processed: {summary['groups']}, duplicates deactivated: {summary['deactivated']}"
            )
        )
