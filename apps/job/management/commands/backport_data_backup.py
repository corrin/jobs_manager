import datetime
import gzip
import json
import os
import subprocess

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection
from faker import Faker


class Command(BaseCommand):
    help = "Backs up necessary production data, excluding Xero-related models."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting data backup..."))

        # Define models to include
        INCLUDE_MODELS = [
            "job.Job",
            "job.JobPricing",
            "job.JobPart",
            "job.MaterialEntry",
            "job.AdjustmentEntry",
            "job.JobEvent",
            "job.JobFile",
            "timesheet.TimeEntry",
            "accounts.Staff",
            "client.Client",
            "client.ClientContact",
            # 'purchasing.PurchaseOrder',     # Xero-owned, will be synced from Xero
            # 'purchasing.PurchaseOrderLine', # Xero-owned, will be synced from Xero
            # 'purchasing.Stock',            # Xero-owned, will be synced from Xero
            "quoting.SupplierPriceList",
            "quoting.SupplierProduct",
            "contenttypes",  # Django internal - needed for migrations
        ]

        # Define the output directory and filename
        backup_dir = os.path.join(settings.BASE_DIR, "restore")
        os.makedirs(backup_dir, exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        env_name = "dev" if settings.DEBUG else "prod"
        output_filename = f"{env_name}_backup_{timestamp}.json.gz"
        output_path = os.path.join(backup_dir, output_filename)

        self.stdout.write(f"Backup will be saved to: {output_path}")
        self.stdout.write(f"Models to be backed up: {', '.join(INCLUDE_MODELS)}")

        try:
            # Step 1: Use Django's dumpdata for clean serialization
            cmd = ["python", "manage.py", "dumpdata"] + INCLUDE_MODELS
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            # Step 2: Add migrations data manually
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id, app, name, applied FROM django_migrations ORDER BY id"
                )
                migrations_rows = cursor.fetchall()

            # Convert migrations to Django fixture format
            migrations_data = []
            for row in migrations_rows:
                migrations_data.append(
                    {
                        "model": "migrations.migration",
                        "pk": row[0],
                        "fields": {
                            "app": row[1],
                            "name": row[2],
                            "applied": row[3].isoformat() if row[3] else None,
                        },
                    }
                )

            # Step 3: Parse and combine data
            data = json.loads(result.stdout)
            data.extend(migrations_data)
            fake = Faker()

            self.stdout.write(
                f"Anonymizing {len(data)} records "
                f"(including {len(migrations_data)} migrations)..."
            )

            for item in data:
                self.anonymize_item(item, fake)

            # Step 3: Write anonymized data (compressed)
            with gzip.open(output_path, "wt", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            self.stdout.write(
                self.style.SUCCESS(
                    f"Data backup completed successfully to {output_path}"
                )
            )

        except subprocess.CalledProcessError as e:
            self.stdout.write(self.style.ERROR(f"dumpdata failed: {e.stderr}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error during data backup: {e}"))
            if os.path.exists(output_path):
                os.remove(output_path)

    def anonymize_item(self, item, fake):
        """Anonymize PII fields in the serialized item"""
        model = item["model"]
        fields = item["fields"]

        if model == "accounts.staff":
            fields["first_name"] = fake.first_name()
            fields["last_name"] = fake.last_name()
            if fields["preferred_name"]:
                fields["preferred_name"] = fake.first_name()
            if fields["email"]:
                fields["email"] = fake.email()

        elif model == "client.client":
            # Don't anonymize the shop client (preserve for system functionality)
            if item["pk"] == "00000000-0000-0000-0000-000000000001":
                # Special handling of the shop client
                fields["name"] = "Demo Company Shop"
            else:
                fields["name"] = fake.company()
                if fields["primary_contact_name"]:
                    fields["primary_contact_name"] = fake.name()
                if fields["primary_contact_email"]:
                    fields["primary_contact_email"] = fake.email()
                if fields["email"]:
                    fields["email"] = fake.email()
                if fields["phone"]:
                    fields["phone"] = fake.phone_number()

        elif model == "client.clientcontact":
            fields["name"] = fake.name()
            if fields["email"]:
                fields["email"] = fake.email()
            if fields["phone"]:
                fields["phone"] = fake.phone_number()

        elif model == "job.job":
            if fields["contact_person"]:
                fields["contact_person"] = fake.name()
            if fields["contact_email"]:
                fields["contact_email"] = fake.email()
            if fields["contact_phone"]:
                fields["contact_phone"] = fake.phone_number()
