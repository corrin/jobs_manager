"""
Management command to create test quote data for frontend testing.
"""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.job.models import CostLine, CostSet, Job


class Command(BaseCommand):
    help = "Create test quote data with realistic values for frontend testing"

    def add_arguments(self, parser):
        parser.add_argument(
            "--job-id",
            type=str,
            help="Specific job ID to add test data to (default: first available job)",
        )

    def handle(self, *args, **options):
        try:
            # Get job to update
            if options["job_id"]:
                job = Job.objects.get(pk=options["job_id"])
            else:
                job = Job.objects.first()

            if not job:
                self.stdout.write(self.style.ERROR("No jobs found in database"))
                return

            self.stdout.write(
                f"Creating test quote data for job: {job.name} ({job.id})"
            )

            with transaction.atomic():
                # Get or create a quote CostSet
                quote_costset = job.get_latest("quote")
                if not quote_costset:
                    # Create new quote costset
                    quote_costset = CostSet.objects.create(
                        job=job,
                        kind="quote",
                        rev=1,
                        summary={
                            "cost": Decimal("0"),
                            "rev": Decimal("0"),
                            "hours": Decimal("0"),
                        },
                    )
                    # Set as latest quote
                    job.set_latest("quote", quote_costset)
                    self.stdout.write(f"Created new quote costset: {quote_costset.id}")
                else:
                    self.stdout.write(
                        f"Using existing quote costset: {quote_costset.id}"
                    )

                # Clear existing cost lines
                quote_costset.cost_lines.all().delete()

                # Create realistic test cost lines
                test_lines = [
                    {
                        "kind": "time",
                        "desc": "Project Planning and Design",
                        "quantity": Decimal("8.0"),
                        "unit_cost": Decimal("50.00"),
                        "unit_rev": Decimal("85.00"),
                    },
                    {
                        "kind": "time",
                        "desc": "Development Work",
                        "quantity": Decimal("24.0"),
                        "unit_cost": Decimal("55.00"),
                        "unit_rev": Decimal("90.00"),
                    },
                    {
                        "kind": "time",
                        "desc": "Testing and QA",
                        "quantity": Decimal("6.0"),
                        "unit_cost": Decimal("45.00"),
                        "unit_rev": Decimal("75.00"),
                    },
                    {
                        "kind": "material",
                        "desc": "Software Licenses",
                        "quantity": Decimal("3.0"),
                        "unit_cost": Decimal("120.00"),
                        "unit_rev": Decimal("180.00"),
                    },
                    {
                        "kind": "material",
                        "desc": "Hardware Components",
                        "quantity": Decimal("5.0"),
                        "unit_cost": Decimal("75.00"),
                        "unit_rev": Decimal("120.00"),
                    },
                    {
                        "kind": "material",
                        "desc": "Office Supplies",
                        "quantity": Decimal("1.0"),
                        "unit_cost": Decimal("85.50"),
                        "unit_rev": Decimal("125.00"),
                    },
                ]

                # Create cost lines
                for line_data in test_lines:
                    CostLine.objects.create(cost_set=quote_costset, **line_data)

                # Calculate and update totals
                total_cost = Decimal("0")
                total_rev = Decimal("0")
                total_hours = Decimal("0")

                for line in quote_costset.cost_lines.all():
                    line_cost = line.quantity * line.unit_cost
                    line_rev = line.quantity * line.unit_rev
                    total_cost += line_cost
                    total_rev += line_rev

                    if line.kind == "time":
                        total_hours += line.quantity

                # Update summary
                quote_costset.summary = {
                    "cost": float(total_cost),
                    "rev": float(total_rev),
                    "hours": float(total_hours),
                }
                quote_costset.save()

                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ Test quote data created successfully!\n"
                        f"   - Cost Lines: {quote_costset.cost_lines.count()}\n"
                        f"   - Total Cost: ${total_cost}\n"
                        f"   - Total Revenue: ${total_rev}\n"
                        f"   - Total Hours: {total_hours}\n"
                        f"   - Job ID: {job.id}\n"
                        f"   - Quote CostSet ID: {quote_costset.id}"
                    )
                )

        except Job.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f"Job with ID {options['job_id']} not found")
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error creating test data: {str(e)}"))
