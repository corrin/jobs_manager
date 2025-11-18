import requests
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from xero_python.identity import IdentityApi
from xero_python.project import ProjectApi

from apps.accounts.models import Staff
from apps.timesheet.services import PayrollEmployeeSyncService
from apps.workflow.api.xero.payroll import (
    get_earnings_rates,
    get_employees,
    get_leave_types,
    get_pay_runs,
    get_payroll_calendars,
)
from apps.workflow.api.xero.xero import api_client, get_tenant_id, get_valid_token
from apps.workflow.models import XeroToken
from apps.workflow.models.company_defaults import CompanyDefaults


def get_employees_simple_dev():
    """
    DEV ONLY: Fetch employee basic info for demo company with invalid contractors.

    Returns simple dicts with just: employee_id, first_name, last_name, email.
    Skips contractors without dateOfBirth that crash the xero-python library.
    """
    token = XeroToken.objects.first()
    tenant_id = get_tenant_id()

    headers = {
        "Authorization": f"Bearer {token.access_token}",
        "Xero-Tenant-Id": tenant_id,
        "Accept": "application/json",
    }

    response = requests.get(
        "https://api.xero.com/payroll.xro/2.0/Employees", headers=headers
    )
    response.raise_for_status()

    raw_employees = response.json().get("employees", [])

    # Extract only needed fields, skip contractors (no dateOfBirth)
    employees = []
    skipped = 0
    for emp in raw_employees:
        if emp.get("dateOfBirth"):
            employees.append(
                {
                    "employee_id": emp.get("employeeID"),
                    "first_name": emp.get("firstName"),
                    "last_name": emp.get("lastName"),
                    "email": emp.get("email"),
                }
            )
        else:
            skipped += 1

    return employees, skipped


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
        parser.add_argument(
            "--payroll-employees",
            action="store_true",
            help="Get Xero Payroll employees",
        )
        parser.add_argument(
            "--payroll-rates",
            action="store_true",
            help="Get Xero Payroll earnings rates",
        )
        parser.add_argument(
            "--payroll-calendars",
            action="store_true",
            help="Get Xero Payroll calendars",
        )
        parser.add_argument(
            "--payroll-leave-types",
            action="store_true",
            help="Get Xero Payroll leave types",
        )
        parser.add_argument(
            "--payroll-pay-runs",
            action="store_true",
            help="Get Xero Payroll pay runs",
        )
        parser.add_argument(
            "--configure-payroll",
            action="store_true",
            help="Interactively configure payroll earnings rate mappings",
        )
        parser.add_argument(
            "--link-staff",
            action="store_true",
            help="Link staff to Xero Payroll employees by matching email addresses",
        )
        parser.add_argument(
            "--link-staff-emails",
            help="Comma separated list of staff emails to limit linking operations",
        )
        parser.add_argument(
            "--link-staff-create-missing",
            action="store_true",
            help="When linking staff, create missing Xero Payroll employees automatically",
        )
        parser.add_argument(
            "--link-staff-dry-run",
            action="store_true",
            help="Preview staff linking/creation without modifying Xero or the database",
        )
        parser.add_argument(
            "--raw-api",
            action="store_true",
            help="DEV ONLY: Use the RAW API workaround for demo company with invalid contractor data",
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

        if options["payroll_employees"]:
            self.get_payroll_employees(use_raw_api=options.get("raw_api", False))
            return

        if options["payroll_rates"]:
            self.get_payroll_rates()
            return

        if options["payroll_calendars"]:
            self.get_payroll_calendars()
            return

        if options["payroll_leave_types"]:
            self.get_payroll_leave_types()
            return

        if options["payroll_pay_runs"]:
            self.get_payroll_pay_runs()
            return

        if options["configure_payroll"]:
            self.configure_payroll()
            return

        if options["link_staff"]:
            self.link_staff(options)
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
            users_response = project_api.get_project_users(xero_tenant_id=tenant_id)

            self.stdout.write(
                f"Xero Users (Projects API) - Total: {len(users_response.items)}:"
            )
            self.stdout.write("---------------------------")

            for i, user in enumerate(users_response.items, 1):
                self.stdout.write(f"Entry #{i}:")
                self.stdout.write(f"  User ID: {user.user_id}")
                self.stdout.write(f"  Name: {user.name}")
                self.stdout.write(f"  Email: {user.email}")
                # Show all available attributes to help debug
                self.stdout.write(f"  Full object: {user.to_dict()}")
                self.stdout.write("---------------------------")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to get users: {e}"))

    def get_payroll_employees(self, use_raw_api):
        """Get Xero Payroll employees"""
        self.stdout.write(self.style.SUCCESS("\n=== Xero Payroll Employees ===\n"))

        try:
            if use_raw_api:
                # DEV ONLY workaround for demo company
                employees, skipped = get_employees_simple_dev()
                if skipped > 0:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Skipped {skipped} contractors (no dateOfBirth)\n"
                        )
                    )
            else:
                # Proper API - use xero-python library
                employee_objects = get_employees()
                employees = [
                    {
                        "employee_id": emp.employee_id,
                        "first_name": emp.first_name,
                        "last_name": emp.last_name,
                        "email": emp.email,
                    }
                    for emp in employee_objects
                ]

            if not employees:
                self.stdout.write(
                    self.style.WARNING("No employees found in Xero Payroll")
                )
                return

            for emp in employees:
                self.stdout.write(
                    f"ID: {emp['employee_id']}\n"
                    f"  Name: {emp['first_name']} {emp['last_name']}\n"
                    f"  Email: {emp['email'] or 'N/A'}\n"
                )

            self.stdout.write(
                self.style.SUCCESS(f"\nTotal: {len(employees)} employees")
            )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to fetch employees: {e}"))

    def get_payroll_rates(self):
        """Get Xero Payroll earnings rates"""
        self.stdout.write(self.style.SUCCESS("\n=== Xero Payroll Earnings Rates ===\n"))

        try:
            rates = get_earnings_rates()

            if not rates:
                self.stdout.write(
                    self.style.WARNING("No earnings rates found in Xero Payroll")
                )
                return

            for rate in rates:
                self.stdout.write(
                    f"ID: {rate['id']}\n"
                    f"  Name: {rate['name']}\n"
                    f"  Type: {rate['earnings_type']}\n"
                    f"  Rate Type: {rate['rate_type']}\n"
                    f"  Units: {rate['type_of_units']}\n"
                )

            self.stdout.write(
                self.style.SUCCESS(f"\nTotal: {len(rates)} earnings rates")
            )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to fetch earnings rates: {e}"))

    def get_payroll_calendars(self):
        """Get Xero Payroll calendars"""
        self.stdout.write(self.style.SUCCESS("\n=== Xero Payroll Calendars ===\n"))

        try:
            calendars = get_payroll_calendars()

            if not calendars:
                self.stdout.write(
                    self.style.WARNING("No payroll calendars found in Xero Payroll")
                )
                return

            for cal in calendars:
                self.stdout.write(
                    f"ID: {cal['id']}\n"
                    f"  Name: {cal['name']}\n"
                    f"  Type: {cal['calendar_type']}\n"
                    f"  Period: {cal['period_start_date']} to {cal['period_end_date']}\n"
                    f"  Payment Date: {cal['payment_date']}\n"
                )

            self.stdout.write(
                self.style.SUCCESS(f"\nTotal: {len(calendars)} calendars")
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Failed to fetch payroll calendars: {e}")
            )

    def get_payroll_leave_types(self):
        """Get Xero Payroll leave types"""
        self.stdout.write(self.style.SUCCESS("\n=== Xero Payroll Leave Types ===\n"))

        try:
            leave_types = get_leave_types()

            if not leave_types:
                self.stdout.write(
                    self.style.WARNING("No leave types found in Xero Payroll")
                )
                return

            for lt in leave_types:
                self.stdout.write(f"ID: {lt['id']}\n" f"  Name: {lt['name']}\n")

            self.stdout.write(
                self.style.SUCCESS(f"\nTotal: {len(leave_types)} leave types")
            )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to fetch leave types: {e}"))

    def get_payroll_pay_runs(self):
        """Get Xero Payroll pay runs"""
        self.stdout.write(self.style.SUCCESS("\n=== Xero Payroll Pay Runs ===\n"))

        try:
            pay_runs = get_pay_runs()

            if not pay_runs:
                self.stdout.write(
                    self.style.WARNING("No pay runs found in Xero Payroll")
                )
                return

            for pr in pay_runs:
                self.stdout.write(f"Pay Run ID: {pr['pay_run_id']}")
                self.stdout.write(
                    f"  Period: {pr['period_start_date']} to {pr['period_end_date']}"
                )
                self.stdout.write(f"  Payment Date: {pr['payment_date']}")
                self.stdout.write(f"  Status: {pr['pay_run_status']}")
                self.stdout.write(f"  Type: {pr['pay_run_type']}")
                self.stdout.write(f"  Calendar ID: {pr['payroll_calendar_id']}\n")

            self.stdout.write(self.style.SUCCESS(f"\nTotal: {len(pay_runs)} pay runs"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to fetch pay runs: {e}"))

    def configure_payroll(self):
        """Interactively configure Xero Payroll mappings"""
        self.stdout.write(
            self.style.SUCCESS("\n=== Configure Xero Payroll Mappings ===\n")
        )

        try:
            # Fetch available leave types
            leave_types = get_leave_types()
            if not leave_types:
                self.stdout.write(
                    self.style.ERROR(
                        "No leave types found. Cannot configure leave mappings."
                    )
                )
                return

            # Fetch available earnings rates
            rates = get_earnings_rates()
            if not rates:
                self.stdout.write(
                    self.style.ERROR(
                        "No earnings rates found. Cannot configure earnings rate mappings."
                    )
                )
                return

            # Display available leave types
            self.stdout.write("\nAvailable leave types:")
            for i, lt in enumerate(leave_types, 1):
                self.stdout.write(f"{i}. {lt['name']} - ID: {lt['id']}")

            # Display available earnings rates
            self.stdout.write("\nAvailable earnings rates:")
            for i, rate in enumerate(rates, 1):
                self.stdout.write(
                    f"{i}. {rate['name']} ({rate['earnings_type']}) - ID: {rate['id']}"
                )

            # Get company defaults
            company_defaults = CompanyDefaults.get_instance()

            # Configure leave types
            self.stdout.write(self.style.SUCCESS("\n--- Leave Types ---"))
            company_defaults.xero_annual_leave_type_id = self._prompt_for_id(
                "Annual Leave", leave_types, company_defaults.xero_annual_leave_type_id
            )
            company_defaults.xero_sick_leave_type_id = self._prompt_for_id(
                "Sick Leave", leave_types, company_defaults.xero_sick_leave_type_id
            )
            company_defaults.xero_other_leave_type_id = self._prompt_for_id(
                "Other Leave", leave_types, company_defaults.xero_other_leave_type_id
            )
            company_defaults.xero_unpaid_leave_type_id = self._prompt_for_id(
                "Unpaid Leave", leave_types, company_defaults.xero_unpaid_leave_type_id
            )

            # Configure work rates
            self.stdout.write(self.style.SUCCESS("\n--- Work Time Rates ---"))
            company_defaults.xero_ordinary_earnings_rate_id = self._prompt_for_rate(
                "Ordinary Time (1.0x)",
                rates,
                company_defaults.xero_ordinary_earnings_rate_id,
            )
            company_defaults.xero_time_half_earnings_rate_id = self._prompt_for_rate(
                "Time and a Half (1.5x)",
                rates,
                company_defaults.xero_time_half_earnings_rate_id,
            )
            company_defaults.xero_double_time_earnings_rate_id = self._prompt_for_rate(
                "Double Time (2.0x)",
                rates,
                company_defaults.xero_double_time_earnings_rate_id,
            )

            # Save
            company_defaults.save()

            self.stdout.write(
                self.style.SUCCESS("\n✓ Payroll mappings saved successfully!")
            )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to configure mappings: {e}"))

    def _prompt_for_id(self, label, items, current_value):
        """Prompt user to select an ID from a list of items (leave types, earnings rates, etc.)"""
        current_display = current_value if current_value else "Not set"
        prompt = f"\n{label} (current: {current_display})\nEnter ID (or press Enter to skip): "

        item_id = input(prompt).strip()

        if not item_id:
            return current_value  # Keep existing value

        # Validate that the ID exists
        if not any(item["id"] == item_id for item in items):
            self.stdout.write(
                self.style.WARNING(f"Warning: {item_id} not found in available items")
            )
            confirm = input("Use this ID anyway? (y/N): ").strip().lower()
            if confirm != "y":
                return current_value

        return item_id

    def link_staff(self, options):
        """Link Staff rows to Xero Payroll employees and optionally create missing ones."""
        emails_option = options.get("link_staff_emails")
        create_missing = options.get("link_staff_create_missing", False)
        dry_run = options.get("link_staff_dry_run", False)

        queryset = Staff.objects.filter(date_left__isnull=True)
        if emails_option:
            emails = [
                email.strip() for email in emails_option.split(",") if email.strip()
            ]
            if not emails:
                self.stdout.write(
                    self.style.WARNING(
                        "No valid emails provided via --link-staff-emails; nothing to do."
                    )
                )
                return

            email_filter = Q()
            for email in emails:
                email_filter |= Q(email__iexact=email)
            queryset = queryset.filter(email_filter)

        if not queryset.exists():
            self.stdout.write(
                self.style.WARNING(
                    "No staff records matched the provided filters. Aborting."
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Processing {queryset.count()} staff member(s) "
                f"(dry run={dry_run}, create_missing={create_missing})"
            )
        )

        try:
            summary = PayrollEmployeeSyncService.sync_staff(
                staff_queryset=queryset,
                dry_run=dry_run,
                allow_create=create_missing,
            )
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        self._print_link_staff_summary(summary)

    def _print_link_staff_summary(self, summary):
        total = summary.get("total", 0)
        dry_run = summary.get("dry_run", False)
        self.stdout.write(f"Total evaluated: {total}")
        self.stdout.write(f"Dry run: {'Yes' if dry_run else 'No'}")

        linked = summary.get("linked", [])
        created = summary.get("created", [])
        already = summary.get("already_linked", [])
        missing = summary.get("missing", [])

        if linked:
            self.stdout.write(self.style.SUCCESS(f"Linked {len(linked)} staff:"))
            for entry in linked:
                self.stdout.write(
                    f"  {entry['email']} -> {entry['xero_employee_id']} "
                    f"(Xero: {entry['xero_name'] or 'N/A'})"
                )

        if created:
            verb = "Would create" if dry_run else "Created"
            self.stdout.write(
                self.style.SUCCESS(f"{verb} {len(created)} Xero payroll employee(s):")
            )
            for entry in created:
                target = entry["xero_employee_id"] or "NEW"
                self.stdout.write(f"  {entry['email']} -> {target}")

        if already:
            self.stdout.write(
                self.style.WARNING(f"Skipped {len(already)} already-linked staff:")
            )
            for entry in already:
                self.stdout.write(f"  {entry['email']} (existing link)")

        if missing:
            self.stdout.write(
                self.style.ERROR(
                    f"{len(missing)} staff have no matching Xero employee. "
                    "Rerun with --link-staff-create-missing once their data is complete."
                )
            )
            for entry in missing:
                self.stdout.write(f"  {entry['email']}")

    def _prompt_for_rate(self, label, rates, current_value):
        """Prompt user to select an earnings rate"""
        current_display = current_value if current_value else "Not set"
        prompt = f"\n{label} (current: {current_display})\nEnter earnings rate ID (or press Enter to skip): "

        rate_id = input(prompt).strip()

        if not rate_id:
            return current_value  # Keep existing value

        # Validate that the rate ID exists
        if not any(r["id"] == rate_id for r in rates):
            self.stdout.write(
                self.style.WARNING(f"Warning: {rate_id} not found in available rates")
            )
            confirm = input("Use this ID anyway? (y/N): ").strip().lower()
            if confirm != "y":
                return current_value

        return rate_id
