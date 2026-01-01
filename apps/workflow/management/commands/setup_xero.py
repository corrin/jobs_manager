import logging

from django.core.management.base import BaseCommand
from xero_python.accounting import AccountingApi
from xero_python.identity import IdentityApi

from apps.workflow.api.xero.xero import api_client, get_valid_token
from apps.workflow.models import CompanyDefaults

logger = logging.getLogger("xero")


class Command(BaseCommand):
    help = "Configure Xero tenant ID and shortcode for this installation"

    def handle(self, *args, **options):
        self.stdout.write("Setting up Xero connection...")

        # Step 1: Check for valid token
        token = get_valid_token()
        if not token:
            self.stdout.write(
                self.style.ERROR(
                    "No valid Xero token found.\n"
                    "Run: python manage.py interact_with_xero --auth"
                )
            )
            return

        # Step 2: Get connected organisations
        try:
            identity_api = IdentityApi(api_client)
            connections = identity_api.get_connections()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to get Xero connections: {e}"))
            raise

        if not connections:
            self.stdout.write(
                self.style.ERROR(
                    "No Xero organisations connected.\n"
                    "Please connect an organisation in Xero first."
                )
            )
            return

        # Step 3: Use first connected organisation
        connection = connections[0]
        tenant_id = connection.tenant_id
        tenant_name = connection.tenant_name

        self.stdout.write(f"Using organisation: {tenant_name}")

        if len(connections) > 1:
            self.stdout.write(
                self.style.WARNING(
                    f"Note: {len(connections)} organisations connected. Using first one."
                )
            )

        # Step 4: Get CompanyDefaults
        company = CompanyDefaults.objects.first()
        if not company:
            self.stdout.write(
                self.style.ERROR(
                    "No CompanyDefaults found.\n"
                    "Run: python manage.py loaddata apps/workflow/fixtures/company_defaults.json"
                )
            )
            return

        # Step 5: Fetch organisation shortcode for deep linking
        accounting_api = AccountingApi(api_client)
        org_response = accounting_api.get_organisations(xero_tenant_id=tenant_id)

        if not org_response or not org_response.organisations:
            self.stdout.write(
                self.style.ERROR("Failed to fetch organisation details from Xero.")
            )
            return

        shortcode = org_response.organisations[0].short_code

        # Step 6: Save to CompanyDefaults
        company.xero_tenant_id = tenant_id
        company.xero_shortcode = shortcode
        company.save()

        self.stdout.write(self.style.SUCCESS(f"Tenant ID: {tenant_id}"))
        self.stdout.write(self.style.SUCCESS(f"Shortcode: {shortcode}"))
        self.stdout.write(self.style.SUCCESS("Xero setup complete."))
        self.stdout.write("")
        self.stdout.write("Next step: python manage.py start_xero_sync")
