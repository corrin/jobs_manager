import logging

from django.core.management.base import BaseCommand
from django.db import close_old_connections
from xero_python.identity import IdentityApi

from apps.client.models import Client
from apps.workflow.api.xero.xero import api_client, get_valid_token
from apps.workflow.models import CompanyDefaults

logger = logging.getLogger("xero")


class Command(BaseCommand):
    help = "Setup shop client with Xero contact ID for development"

    def add_arguments(self, parser):
        parser.add_argument(
            "--full-sync",
            action="store_true",
            help="Run a full Xero sync after setting up the shop client (default: skip)",
        )

    def handle(self, *args, **options):
        # Setup logging
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        self.stdout.write(
            self.style.SUCCESS("Setting up shop client for development...")
        )

        # Step 1: Check for valid token
        token = get_valid_token()
        if not token:
            self.stdout.write(
                self.style.ERROR(
                    "No valid Xero token found. Please authenticate with Xero first by visiting the app."
                )
            )
            return

        # Step 2: Get available tenants
        try:
            identity_api = IdentityApi(api_client)
            connections = identity_api.get_connections()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to get Xero connections: {e}"))
            return

        # Step 3: Find Demo Company
        demo_tenant_id = None
        for conn in connections:
            if "Demo Company" in conn.tenant_name:
                demo_tenant_id = conn.tenant_id
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Found Demo Company: {conn.tenant_name} ({demo_tenant_id})"
                    )
                )
                break

        if not demo_tenant_id:
            self.stdout.write(
                self.style.ERROR(
                    "Demo Company not found in available Xero connections."
                )
            )
            self.stdout.write("Available organizations:")
            for conn in connections:
                self.stdout.write(f"  - {conn.tenant_name} ({conn.tenant_id})")
            return

        # Step 4: Update CompanyDefaults
        try:
            company = CompanyDefaults.objects.first()
            if not company:
                self.stdout.write(
                    self.style.ERROR(
                        "No CompanyDefaults found. Please create one first."
                    )
                )
                return

            old_tenant_id = company.xero_tenant_id
            company.xero_tenant_id = demo_tenant_id
            company.save()

            self.stdout.write(
                self.style.SUCCESS(
                    f"Updated CompanyDefaults Xero tenant ID from {old_tenant_id} to {demo_tenant_id}"
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Failed to update CompanyDefaults: {e}")
            )
            return

        # Step 5: Sync shop client only
        self.stdout.write(self.style.SUCCESS("Syncing shop client from Xero..."))

        # TODO: Call CompanyDefaults to get the Shop Client name (future)
        # For development, we only sync "Demo Company Shop"
        shop_client_name = "Demo Company Shop"

        self.stdout.write(f"Looking for shop client: {shop_client_name}")

        # First check if shop client exists locally
        shop_client = Client.objects.filter(name=shop_client_name).first()

        if shop_client and shop_client.xero_contact_id:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{shop_client_name} already has Xero contact ID: {shop_client.xero_contact_id}"
                )
            )
        else:
            # Try to find and sync from Xero
            try:
                from xero_python.accounting import AccountingApi

                from apps.workflow.api.xero.xero import get_tenant_id

                accounting_api = AccountingApi(api_client)
                xero_tenant_id = get_tenant_id()

                # Search for the client in Xero
                response = accounting_api.get_contacts(
                    xero_tenant_id, where=f'Name=="{shop_client_name}"'
                )

                if response.contacts:
                    # Found in Xero, sync it
                    self.stdout.write(f"Found {shop_client_name} in Xero, syncing...")
                    from apps.workflow.api.xero.sync import sync_clients

                    sync_clients(response.contacts)

                    # Verify it worked
                    shop_client = Client.objects.filter(name=shop_client_name).first()
                    if shop_client and shop_client.xero_contact_id:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Successfully synced {shop_client_name} with Xero contact ID: {shop_client.xero_contact_id}"
                            )
                        )
                    else:
                        self.stdout.write(
                            self.style.ERROR("Sync failed - client not created locally")
                        )
                        return
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            f"{shop_client_name} not found in Xero. "
                            "Please create it in Xero first:\n"
                            "1. Go to your Xero Demo Company\n"
                            "2. Navigate to Contacts → Add Contact\n"
                            "3. Name: 'Demo Company Shop' (exactly this)\n"
                            "4. Save the contact"
                        )
                    )
                    return

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Failed to search/sync shop client: {e}")
                )
                return

        # Step 6: Optionally run full sync
        if options["full_sync"]:
            self.stdout.write(
                self.style.SUCCESS("Running full Xero sync as requested...")
            )
            try:
                from apps.workflow.api.xero.sync import synchronise_xero_data

                sync_count = 0
                for message in synchronise_xero_data():
                    sync_count += 1
                    # Only show progress messages every 100 items to avoid spam
                    if sync_count % 100 == 0:
                        message.get("severity", "info")
                        msg_text = message.get("message", "No message")
                        entity = message.get("entity", "N/A")
                        progress = message.get("progress", "N/A")

                        progress_display = (
                            "N/A"
                            if not isinstance(progress, (int, float))
                            else f"{progress:.2f}"
                        )
                        self.stdout.write(
                            f"Sync Progress ({entity}): {msg_text} (Progress: {progress_display})"
                        )

                self.stdout.write(
                    self.style.SUCCESS("Full Xero sync completed successfully.")
                )
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Full Xero sync failed: {e}"))
                logger.error(f"Error during full Xero sync: {e}", exc_info=True)
                return
        else:
            self.stdout.write(
                "Skipping full Xero sync (default). Use --full-sync to run it."
            )

        close_old_connections()
        self.stdout.write(self.style.SUCCESS("Setup completed!"))
