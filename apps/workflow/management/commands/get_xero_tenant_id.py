from django.core.management.base import BaseCommand
from xero_python.identity import IdentityApi

from apps.workflow.api.xero.xero import api_client, get_valid_token
from apps.workflow.models.company_defaults import CompanyDefaults


class Command(BaseCommand):
    help = "Get available Xero tenant IDs and names"

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-set",
            action="store_true",
            help="Do not automatically set the tenant ID if only one tenant is found",
        )

    def handle(self, **options):
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

        self.stdout.write("Available Xero Organizations:")
        self.stdout.write("-----------------------------")
        for conn in connections:
            self.stdout.write(self.style.SUCCESS(f"Tenant ID: {conn.tenant_id}"))
            self.stdout.write(f"Name: {conn.tenant_name}")
            self.stdout.write("-----------------------------")

        # If only one tenant and --no-set not specified, automatically set it
        if len(connections) == 1 and not options["no_set"]:
            tenant_id = connections[0].tenant_id
            tenant_name = connections[0].tenant_name

            try:
                company_defaults = CompanyDefaults.get_instance()
                company_defaults.xero_tenant_id = tenant_id
                company_defaults.save()

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Automatically set tenant ID to {tenant_id} "
                        f"({tenant_name}) in CompanyDefaults"
                    )
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Failed to set tenant ID in CompanyDefaults: {e}")
                )
        elif len(connections) == 1 and options["no_set"]:
            self.stdout.write(
                self.style.WARNING(
                    "Single tenant found but --no-set specified, "
                    "not updating CompanyDefaults"
                )
            )
        elif len(connections) > 1:
            self.stdout.write(
                self.style.WARNING(
                    f"Multiple tenants found ({len(connections)}), "
                    "not automatically setting tenant ID"
                )
            )
