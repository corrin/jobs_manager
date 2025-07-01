from django.core.management.base import BaseCommand
from xero_python.identity import IdentityApi

from apps.workflow.api.xero.xero import api_client, get_valid_token


class Command(BaseCommand):
    help = "Get available Xero tenant IDs and names"

    def handle(self, *args, **options):
        # First check we have a valid token
        token = get_valid_token()
        if not token:
            self.stdout.write(
                self.style.ERROR(
                    "No valid Xero token found. Please authenticate with Xero first."
                )
            )
            return

        identity_api = IdentityApi(api_client)
        connections = identity_api.get_connections()

        self.stdout.write("\nAvailable Xero Organizations:")
        self.stdout.write("-----------------------------")
        for conn in connections:
            self.stdout.write(self.style.SUCCESS(f"Tenant ID: {conn.tenant_id}"))
            self.stdout.write(f"Name: {conn.tenant_name}")
            self.stdout.write("-----------------------------")
