import logging
import socket

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection
from dotenv import load_dotenv

from apps.client.models import Client
from apps.job.models import Job
from apps.purchasing.models import Stock
from apps.workflow.api.xero.stock_sync import sync_all_local_stock_to_xero
from apps.workflow.api.xero.sync import seed_clients_to_xero, seed_jobs_to_xero
from apps.workflow.services.error_persistence import persist_and_raise

load_dotenv()

logger = logging.getLogger("xero")


class Command(BaseCommand):
    help = "Seed Xero development tenant with database clients and jobs"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be synced without making changes",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        mode_text = "DRY RUN - " if dry_run else ""
        self.stdout.write(f"{mode_text}Seeding Xero from Database")
        self.stdout.write("=" * 50)

        try:
            # Phase 0: Clear production Xero IDs (always - this is for restore scenarios)
            self.stdout.write("Phase 0: Clearing Production Xero IDs")
            self.clear_production_xero_ids(dry_run)

            # Phase 1: Link/Create contacts
            self.stdout.write("Phase 1: Processing Contacts")
            contacts_processed = self.process_contacts(dry_run)

            # Phase 2: Create projects (only if enabled)
            if settings.XERO_SYNC_PROJECTS:
                self.stdout.write("Phase 2: Processing Projects")
                projects_processed = self.process_projects(dry_run)
            else:
                self.stdout.write(
                    "Phase 2: Skipping Projects (XERO_SYNC_PROJECTS is disabled)"
                )
                projects_processed = 0

            # Phase 3: Sync stock items to Xero
            self.stdout.write("Phase 3: Processing Stock Items")
            stock_processed = self.process_stock_items(dry_run)

            # Summary
            self.stdout.write("COMPLETED")
            self.stdout.write(f"Contacts processed: {contacts_processed}")
            self.stdout.write(f"Projects processed: {projects_processed}")
            self.stdout.write(f"Stock items processed: {stock_processed}")

            if dry_run:
                self.stdout.write("Dry run complete - no changes made")
            else:
                self.stdout.write("Xero seeding complete!")

        except Exception as e:
            logger.error(f"Error during Xero seeding: {e}", exc_info=True)
            persist_and_raise(
                e, additional_context={"operation": "seed_xero_from_database"}
            )

    def process_contacts(self, dry_run):
        """Phase 1: Link/Create contacts for all clients with jobs"""
        # Find clients with jobs that need xero_contact_id
        clients_needing_sync = Client.objects.filter(
            jobs__isnull=False, xero_contact_id__isnull=True
        ).distinct()

        self.stdout.write(
            f"Found {clients_needing_sync.count()} clients needing Xero contact IDs"
        )

        if not clients_needing_sync.exists():
            self.stdout.write("All clients with jobs already have Xero contact IDs")
            return 0

        if dry_run:
            for client in clients_needing_sync[:10]:  # Show first 10
                job_count = client.jobs.count()
                self.stdout.write(
                    f"  • Would process: {client.name} ({job_count} jobs)"
                )
            if clients_needing_sync.count() > 10:
                self.stdout.write(f"  ... and {clients_needing_sync.count() - 10} more")
            return clients_needing_sync.count()

        # Call sync module for bulk processing
        self.stdout.write("Processing clients with Xero sync module...")
        results = seed_clients_to_xero(clients_needing_sync)

        # Report results
        self.stdout.write(
            f"Contacts Summary: {results['linked']} linked, {results['created']} created"
        )

        if results["failed"]:
            self.stdout.write(f"Failed to process {len(results['failed'])} clients:")
            for name in results["failed"][:5]:  # Show first 5 failures
                self.stdout.write(f"  • {name}")
            if len(results["failed"]) > 5:
                self.stdout.write(f"  ... and {len(results['failed']) - 5} more")

        return results["linked"] + results["created"]

    def process_projects(self, dry_run):
        """Phase 2: Create projects for all jobs whose clients have xero_contact_id"""
        # Find jobs that need xero_project_id
        jobs_needing_sync = Job.objects.filter(
            client__xero_contact_id__isnull=False, xero_project_id__isnull=True
        )

        self.stdout.write(
            f"Found {jobs_needing_sync.count()} jobs needing Xero project IDs"
        )

        if not jobs_needing_sync.exists():
            self.stdout.write(
                "All jobs with valid clients already have Xero project IDs"
            )
            return 0

        if dry_run:
            for job in jobs_needing_sync[:10]:  # Show first 10
                self.stdout.write(
                    f"  • Would create project: {job.name} (Client: {job.client.name})"
                )
            if jobs_needing_sync.count() > 10:
                self.stdout.write(f"  ... and {jobs_needing_sync.count() - 10} more")
            return jobs_needing_sync.count()

        # Call sync module for bulk processing
        self.stdout.write("Processing jobs with Xero sync module...")
        results = seed_jobs_to_xero(jobs_needing_sync)

        # Report results
        self.stdout.write(f"Projects Summary: {results['created']} created")

        if results["failed"]:
            self.stdout.write(f"Failed to process {len(results['failed'])} jobs:")
            for name in results["failed"][:5]:  # Show first 5 failures
                self.stdout.write(f"  • {name}")
            if len(results["failed"]) > 5:
                self.stdout.write(f"  ... and {len(results['failed']) - 5} more")

        return results["created"]

    def process_stock_items(self, dry_run):
        """Phase 3: Sync stock items to Xero inventory."""
        # Find stock items that need xero_id
        stock_needing_sync = Stock.objects.filter(
            xero_id__isnull=True, is_active=True
        ).order_by("date")

        self.stdout.write(
            f"Found {stock_needing_sync.count()} stock items needing Xero sync"
        )

        if not stock_needing_sync.exists():
            self.stdout.write("All active stock items already have Xero IDs")
            return 0

        if dry_run:
            for stock in stock_needing_sync[:10]:  # Show first 10
                self.stdout.write(
                    f"  • Would sync: {stock.description} (qty: {stock.quantity}, cost: ${stock.unit_cost})"
                )
            if stock_needing_sync.count() > 10:
                self.stdout.write(f"  ... and {stock_needing_sync.count() - 10} more")
            return stock_needing_sync.count()

        # Call stock sync module for processing
        self.stdout.write("Syncing stock items to Xero...")
        results = sync_all_local_stock_to_xero(limit=None)

        # Report results
        self.stdout.write(
            f"Stock Summary: {results['synced_count']} synced, {results['failed_count']} failed"
        )

        if results["failed_items"]:
            self.stdout.write(
                f"Failed to sync {len(results['failed_items'])} stock items:"
            )
            for item in results["failed_items"][:5]:  # Show first 5 failures
                self.stdout.write(f"  • {item['description']} - {item['reason']}")
            if len(results["failed_items"]) > 5:
                self.stdout.write(f"  ... and {len(results['failed_items']) - 5} more")

        return results["synced_count"]

    def clear_production_xero_ids(self, dry_run):
        """Clear production Xero IDs from all relevant tables."""
        # Safety check - never run on production server
        hostname = socket.gethostname().lower()
        db_name = settings.DATABASES["default"]["NAME"]

        if "msm" in hostname or "prod" in hostname:
            self.stdout.write(
                self.style.ERROR(
                    f"ERROR: Refusing to run on production server: {hostname}"
                )
            )
            self.stdout.write(
                "This operation is only for development environments after production restore."
            )
            return

        self.stdout.write(f"Host: {hostname}")
        self.stdout.write(f"Database: {db_name}")
        self.stdout.write("This will clear Xero IDs from restored production data.")
        self.stdout.write("Records will be re-linked during the sync process.")

        if dry_run:
            self.stdout.write("Dry run - would clear Xero IDs but not making changes")
            return

        tables_cleared = []

        with connection.cursor() as cursor:
            # Clear client contact IDs - allows re-linking by name
            self.stdout.write("Clearing client xero_contact_id values...")
            if self._table_exists(cursor, "workflow_client"):
                cursor.execute(
                    "UPDATE workflow_client SET xero_contact_id = NULL WHERE xero_contact_id IS NOT NULL"
                )
                client_count = cursor.rowcount
                if client_count > 0:
                    tables_cleared.append(f"workflow_client: {client_count} records")
            else:
                self.stdout.write(
                    "  WARNING: workflow_client table not found - skipping"
                )

            # Clear job project IDs - allows fresh project sync
            self.stdout.write("Clearing job xero_project_id values...")
            if self._table_exists(cursor, "workflow_job") and self._column_exists(
                cursor, "workflow_job", "xero_project_id"
            ):
                cursor.execute(
                    "UPDATE workflow_job SET xero_project_id = NULL WHERE xero_project_id IS NOT NULL"
                )
                job_count = cursor.rowcount
                if job_count > 0:
                    tables_cleared.append(f"workflow_job: {job_count} records")
            else:
                self.stdout.write(
                    "  WARNING: workflow_job.xero_project_id column not found - skipping"
                )

            # Clear invoice/bill/quote IDs - prevents duplicates
            self.stdout.write("Clearing accounting xero_id values...")
            for table_name in [
                "accounting_invoice",
                "accounting_bill",
                "accounting_quote",
            ]:
                if self._table_exists(cursor, table_name) and self._column_exists(
                    cursor, table_name, "xero_id"
                ):
                    cursor.execute(
                        f"UPDATE {table_name} SET xero_id = NULL WHERE xero_id IS NOT NULL"
                    )
                    count = cursor.rowcount
                    if count > 0:
                        tables_cleared.append(f"{table_name}: {count} records")

            # Clear purchase order IDs
            self.stdout.write("Clearing purchase order xero_id values...")
            if self._table_exists(
                cursor, "purchasing_purchaseorder"
            ) and self._column_exists(cursor, "purchasing_purchaseorder", "xero_id"):
                cursor.execute(
                    "UPDATE purchasing_purchaseorder SET xero_id = NULL WHERE xero_id IS NOT NULL"
                )
                po_count = cursor.rowcount
                if po_count > 0:
                    tables_cleared.append(
                        f"purchasing_purchaseorder: {po_count} records"
                    )

            # Clear stock item IDs - allows re-creation in UAT Xero tenant
            self.stdout.write("Clearing stock xero_id values...")
            if self._table_exists(cursor, "workflow_stock") and self._column_exists(
                cursor, "workflow_stock", "xero_id"
            ):
                cursor.execute(
                    "UPDATE workflow_stock SET xero_id = NULL WHERE xero_id IS NOT NULL"
                )
                stock_count = cursor.rowcount
                if stock_count > 0:
                    tables_cleared.append(f"workflow_stock: {stock_count} records")

        # Summary
        if tables_cleared:
            self.stdout.write("Cleared Xero IDs from:")
            for table_info in tables_cleared:
                self.stdout.write(f"  • {table_info}")
        else:
            self.stdout.write("No Xero IDs found to clear")

    def _table_exists(self, cursor, table_name):
        """Check if a table exists in the database."""
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = %s AND table_name = %s
        """,
            [settings.DATABASES["default"]["NAME"], table_name],
        )
        return cursor.fetchone()[0] > 0

    def _column_exists(self, cursor, table_name, column_name):
        """Check if a column exists in a table."""
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s AND column_name = %s
        """,
            [settings.DATABASES["default"]["NAME"], table_name, column_name],
        )
        return cursor.fetchone()[0] > 0
