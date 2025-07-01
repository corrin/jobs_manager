from django.core.management.base import BaseCommand

from apps.client.models import Client
from apps.job.models import Job
from apps.workflow.models import CompanyDefaults


class Command(BaseCommand):
    help = "Create shop jobs for internal purposes"

    def handle(self, *args, **kwargs):
        # Define shop job details
        shop_jobs = [
            {
                "name": "Business Development",
                "description": "Sales without a specific client",
            },
            {
                "name": "Bench - busy work",
                "description": (
                    "Busy work not directly tied to client jobs. "
                    "Could slip without significant issues"
                ),
            },
            {
                "name": "Worker Admin",
                "description": (
                    "Mask fittings, meetings, or other worker-related admin. "
                    "Unlike bench, this cannot slip much"
                ),
            },
            {
                "name": "Office Admin",
                "description": "General office administration tasks",
            },
            {"name": "Annual Leave", "description": "Annual leave taken by workers"},
            {"name": "Sick Leave", "description": "Sick leave taken by workers"},
            {
                "name": "Other Leave",
                "description": "Other types of leave taken by workers",
            },
            {"name": "Travel", "description": "Travel for work purposes"},
            {
                "name": "Training",
                "description": "Training sessions for upskilling workers",
            },
        ]

        # Get the shop client from company defaults
        company_defaults = CompanyDefaults.objects.first()
        if not company_defaults:
            self.stdout.write(
                self.style.ERROR(
                    "CompanyDefaults not found. Please configure company defaults first."
                )
            )
            return

        if not company_defaults.shop_client_name:
            self.stdout.write(
                self.style.ERROR("Shop client name not configured in CompanyDefaults.")
            )
            return

        try:
            shop_client = Client.objects.get(name=company_defaults.shop_client_name)
        except Client.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    f"Shop client '{company_defaults.shop_client_name}' not found."
                )
            )
            return
        except Client.MultipleObjectsReturned:
            self.stdout.write(
                self.style.ERROR(
                    f"Multiple clients found with name '{company_defaults.shop_client_name}'. Please resolve duplicates."
                )
            )
            return

        # Iterate through the shop jobs and create them
        for idx, job_details in enumerate(shop_jobs, start=1):
            # Create the job instance
            job = Job(
                name=job_details["name"],
                client=shop_client,
                contact_person="Corrin Lakeland",
                description="",
                material_gauge_quantity=job_details[
                    "description"
                ],  # We put description here, so Kanban doesn't show it
                status="special",
                shop_job=True,  # Changed from shop_job to is_shop_job
                job_is_valid=True,
                paid=False,
                charge_out_rate=0.00,
            )
            job.save()

        self.stdout.write(
            self.style.SUCCESS("Shop jobs have been successfully created.")
        )
