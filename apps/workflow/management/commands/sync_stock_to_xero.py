import logging

from django.core.management.base import BaseCommand
from django.db import models

from apps.purchasing.models import Stock
from apps.workflow.api.xero.stock_sync import (
    fix_long_item_codes,
    sync_all_local_stock_to_xero,
    sync_stock_to_xero,
    update_stock_item_codes,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Sync local stock items to Xero and update missing item codes"

    def add_arguments(self, parser):
        parser.add_argument(
            "--update-codes-only",
            action="store_true",
            help="Only update missing item codes without syncing to Xero",
        )
        parser.add_argument(
            "--fix-long-codes",
            action="store_true",
            help="Fix item codes that are too long for Xero (>30 characters)",
        )
        parser.add_argument(
            "--sync-all",
            action="store_true",
            help="Sync all local stock items to Xero (including those without xero_id)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Limit the number of items to process",
        )
        parser.add_argument(
            "--stock-id",
            type=str,
            help="Sync a specific stock item by ID",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without making changes",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting stock sync to Xero command..."))

        try:
            # Handle specific stock item
            if options["stock_id"]:
                self.handle_single_stock(options["stock_id"], options["dry_run"])
                return

            # Handle fix long codes
            if options["fix_long_codes"]:
                self.handle_fix_long_codes(options["dry_run"])
                return

            # Handle update codes only
            if options["update_codes_only"]:
                self.handle_update_codes(options["dry_run"])
                return

            # Handle sync all
            if options["sync_all"]:
                self.handle_sync_all(options["limit"], options["dry_run"])
                return

            # Default: update codes and sync
            self.stdout.write(
                "Running default operation: update codes + sync new items"
            )

            if not options["dry_run"]:
                # First fix long item codes
                fixed_count = fix_long_item_codes()
                self.stdout.write(
                    self.style.SUCCESS(f"Fixed {fixed_count} long item codes")
                )

                # Then update missing item codes
                updated_count = update_stock_item_codes()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Updated item codes for {updated_count} stock items"
                    )
                )

                # Then sync items without xero_id
                result = sync_all_local_stock_to_xero(limit=options["limit"])
                self.display_sync_results(result)
            else:
                self.show_dry_run_info()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error during stock sync: {str(e)}"))
            logger.exception("Error in sync_stock_to_xero command")
            raise

    def handle_single_stock(self, stock_id, dry_run):
        """Handle syncing a single stock item."""
        try:
            stock_item = Stock.objects.get(id=stock_id)
            self.stdout.write(f"Processing stock item: {stock_item.description}")

            if dry_run:
                self.stdout.write(f"DRY RUN: Would sync stock {stock_id} to Xero")
                self.stdout.write(f"  Description: {stock_item.description}")
                self.stdout.write(
                    f"  Current item_code: {stock_item.item_code or 'None'}"
                )
                self.stdout.write(
                    f"  Has xero_id: {'Yes' if stock_item.xero_id else 'No'}"
                )
                return

            success = sync_stock_to_xero(stock_item)
            if success:
                self.stdout.write(
                    self.style.SUCCESS(f"Successfully synced stock item {stock_id}")
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f"Failed to sync stock item {stock_id}")
                )

        except Stock.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"Stock item with ID {stock_id} not found")
            )

    def handle_fix_long_codes(self, dry_run):
        """Handle fixing long item codes only."""
        if dry_run:
            count = Stock.objects.filter(
                item_code__regex=r"^.{31,}$", is_active=True  # More than 30 characters
            ).count()
            self.stdout.write(f"DRY RUN: Would fix {count} long item codes")
            return

        fixed_count = fix_long_item_codes()
        self.stdout.write(self.style.SUCCESS(f"Fixed {fixed_count} long item codes"))

    def handle_update_codes(self, dry_run):
        """Handle updating item codes only."""
        if dry_run:
            count = Stock.objects.filter(
                models.Q(item_code__isnull=True)
                | models.Q(item_code="")
                | models.Q(item_code__regex=r"^.{31,}$"),
                is_active=True,
            ).count()
            self.stdout.write(
                f"DRY RUN: Would update item codes for {count} stock items"
            )
            return

        updated_count = update_stock_item_codes()
        self.stdout.write(
            self.style.SUCCESS(f"Updated item codes for {updated_count} stock items")
        )

    def handle_sync_all(self, limit, dry_run):
        """Handle syncing all local stock items."""
        if dry_run:
            queryset = Stock.objects.filter(
                xero_id__isnull=True, is_active=True
            ).order_by("created_at")

            if limit:
                queryset = queryset[:limit]

            count = queryset.count()
            self.stdout.write(f"DRY RUN: Would sync {count} stock items to Xero")

            for stock in queryset[:5]:  # Show first 5 as examples
                self.stdout.write(f"  - {stock.description} (ID: {stock.id})")

            if count > 5:
                self.stdout.write(f"  ... and {count - 5} more items")
            return

        result = sync_all_local_stock_to_xero(limit=limit)
        self.display_sync_results(result)

    def show_dry_run_info(self):
        """Show what would be done in default mode."""
        # Count items with long codes
        long_code_count = Stock.objects.filter(
            item_code__regex=r"^.{31,}$", is_active=True
        ).count()

        # Count items needing code updates
        code_update_count = Stock.objects.filter(
            models.Q(item_code__isnull=True)
            | models.Q(item_code="")
            | models.Q(item_code__regex=r"^.{31,}$"),
            is_active=True,
        ).count()

        # Count items needing sync
        sync_count = Stock.objects.filter(xero_id__isnull=True, is_active=True).count()

        self.stdout.write("DRY RUN - Default operation would:")
        self.stdout.write(f"  1. Fix {long_code_count} long item codes")
        self.stdout.write(f"  2. Update item codes for {code_update_count} stock items")
        self.stdout.write(f"  3. Sync {sync_count} stock items to Xero")

    def display_sync_results(self, result):
        """Display sync results in a formatted way."""
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("SYNC RESULTS")
        self.stdout.write("=" * 50)

        self.stdout.write(f"Total items processed: {result['total_items']}")
        self.stdout.write(
            self.style.SUCCESS(f"Successfully synced: {result['synced_count']}")
        )

        if result["failed_count"] > 0:
            self.stdout.write(
                self.style.ERROR(f"Failed to sync: {result['failed_count']}")
            )

            if result["failed_items"]:
                self.stdout.write("\nFailed items:")
                for item in result["failed_items"][:10]:  # Show first 10 failures
                    self.stdout.write(f"  - {item['description']} (ID: {item['id']})")
                    self.stdout.write(f"    Reason: {item['reason']}")

                if len(result["failed_items"]) > 10:
                    remaining = len(result["failed_items"]) - 10
                    self.stdout.write(f"  ... and {remaining} more failed items")

        self.stdout.write(f"\nSuccess rate: {result['success_rate']:.1f}%")
        self.stdout.write("=" * 50)
