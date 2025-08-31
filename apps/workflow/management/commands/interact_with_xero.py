from django.core.management.base import BaseCommand
from xero_python.identity import IdentityApi
from xero_python.project import ProjectApi

from apps.workflow.api.xero.xero import api_client, get_tenant_id, get_valid_token
from apps.workflow.models.company_defaults import CompanyDefaults


class Command(BaseCommand):
    help = "Interactive Xero API utility - get tenant IDs, users, and other data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-set",
            action="store_true",
            help="Do not automatically set the tenant ID if only one tenant is found",
        )
        parser.add_argument(
            "--tenant",
            action="store_true",
            help="Get available Xero tenant IDs and names",
        )
        parser.add_argument(
            "--users",
            action="store_true",
            help="Get Xero users from Projects API",
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

        # Handle specific flags
        if options["users"]:
            self.get_users()
            return

        if options["tenant"]:
            self.get_tenants(options)
            return

        # Default behavior: show tenant IDs (for backwards compatibility)
        self.get_tenants(options)

    def get_tenants(self, options):
        """Get available Xero tenant IDs and names"""
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

    def get_users(self):
        """Get Xero users from Projects API"""
        tenant_id = get_tenant_id()
        if not tenant_id:
            self.stdout.write(
                self.style.ERROR(
                    "No Xero tenant ID configured. Run with --tenant first."
                )
            )
            return

        try:
            project_api = ProjectApi(api_client)
            users = project_api.get_project_users(xero_tenant_id=tenant_id)

            self.stdout.write("Xero Users (Projects API):")
            self.stdout.write("---------------------------")

            for user in users:
                self.stdout.write(f"User ID: {user.user_id}")
                self.stdout.write(f"Name: {user.name}")
                self.stdout.write(f"Email: {user.email}")
                self.stdout.write("---------------------------")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to get users: {e}"))
