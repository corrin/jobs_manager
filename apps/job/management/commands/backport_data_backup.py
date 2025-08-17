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

            # Initialize uniqueness tracking sets for fields that must be unique
            self._used_company_names = set()
            self._used_staff_emails = set()
            self._used_staff_preferred_names = set()

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
                # Ensure unique preferred names
                while True:
                    preferred_name = fake.first_name()
                    if preferred_name not in self._used_staff_preferred_names:
                        self._used_staff_preferred_names.add(preferred_name)
                        fields["preferred_name"] = preferred_name
                        break
            if fields["email"]:
                # Ensure unique emails
                while True:
                    email = fake.email()
                    if email not in self._used_staff_emails:
                        self._used_staff_emails.add(email)
                        fields["email"] = email
                        break
            if fields["raw_ims_data"]:
                raw_data = fields["raw_ims_data"]
                if "EmpNo" in raw_data:
                    raw_data["EmpNo"] = fake.random_int(min=1000, max=9999)
                if "Surname" in raw_data:
                    raw_data["Surname"] = fake.last_name()
                if "FirstNames" in raw_data:
                    raw_data["FirstNames"] = fake.first_name()
                if "PostalAddress1" in raw_data:
                    raw_data["PostalAddress1"] = fake.street_address()
                if "PostalAddress2" in raw_data:
                    raw_data["PostalAddress2"] = fake.city()
                if "PostalAddress3" in raw_data:
                    raw_data["PostalAddress3"] = fake.postcode()
                if "HomePhone" in raw_data:
                    raw_data["HomePhone"] = fake.phone_number()
                if "HomePhone2" in raw_data:
                    raw_data["HomePhone2"] = fake.phone_number()
                if "StartDate" in raw_data:
                    raw_data["StartDate"] = fake.date_between(
                        start_date="-30y", end_date="today"
                    ).isoformat()
                if "BirthDate" in raw_data:
                    raw_data["BirthDate"] = fake.date_of_birth(
                        minimum_age=18, maximum_age=70
                    ).isoformat()
                if "IRDNumber" in raw_data:
                    raw_data["IRDNumber"] = fake.random_int(min=10000000, max=99999999)
                if "ALDueDate" in raw_data:
                    raw_data["ALDueDate"] = fake.date_between(
                        start_date="today", end_date="+1y"
                    ).isoformat()
                if "BankAccount" in raw_data:
                    raw_data["BankAccount"] = fake.iban()
                if "EmailAddress" in raw_data:
                    raw_data["EmailAddress"] = fake.email()

        elif model == "client.client":
            # Don't anonymize the shop client (preserve for system functionality)
            if item["pk"] == "00000000-0000-0000-0000-000000000001":
                # Special handling of the shop client
                fields["name"] = "Demo Company Shop"
                self._used_company_names.add("Demo Company Shop")
            else:
                # Ensure unique company names
                while True:
                    company_name = fake.company()
                    if company_name not in self._used_company_names:
                        self._used_company_names.add(company_name)
                        fields["name"] = company_name
                        break
                if fields["primary_contact_name"]:
                    fields["primary_contact_name"] = fake.name()
                if fields["primary_contact_email"]:
                    fields["primary_contact_email"] = fake.email()
                if fields["email"]:
                    fields["email"] = fake.email()
                if fields["phone"]:
                    fields["phone"] = fake.phone_number()
                if fields["raw_json"]:
                    raw_json = fields["raw_json"]
                    if "_name" in raw_json:
                        raw_json["_name"] = fake.name()
                    if "_email_address" in raw_json:
                        raw_json["_email_address"] = fake.email()
                    if "_bank_account_details" in raw_json:
                        raw_json["_bank_account_details"] = fake.iban()
                    if "_phones" in raw_json:
                        for phone in raw_json["_phones"]:
                            if "_phone_number" in phone and phone["_phone_number"]:
                                phone["_phone_number"] = fake.phone_number()
                    if "_batch_payments" in raw_json and raw_json["_batch_payments"]:
                        batch = raw_json["_batch_payments"]
                        if "_bank_account_number" in batch:
                            batch["_bank_account_number"] = fake.iban()
                        if "_bank_account_name" in batch:
                            batch["_bank_account_name"] = fake.name()

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
            if fields["notes"]:
                fields["notes"] = fake.text(max_nb_chars=200)

        elif model == "job.adjustmententry":
            if "description" not in fields:
                raise KeyError(
                    f"Model {model} missing expected field 'description'. Available fields: {list(fields.keys())}"
                )
            if fields["description"]:
                fields["description"] = fake.sentence(nb_words=8)

        elif model == "job.jobevent":
            if "description" not in fields:
                raise KeyError(
                    f"Model {model} missing expected field 'description'. Available fields: {list(fields.keys())}"
                )
            if fields["description"]:
                fields["description"] = fake.sentence(nb_words=8)

        elif model == "timesheet.timeentry":
            if "description" not in fields:
                raise KeyError(
                    f"Model {model} missing expected field 'description'. Available fields: {list(fields.keys())}"
                )
            if "note" not in fields:
                raise KeyError(
                    f"Model {model} missing expected field 'note'. Available fields: {list(fields.keys())}"
                )
            if fields["description"]:
                fields["description"] = fake.sentence(nb_words=6)
            if fields["note"]:
                fields["note"] = fake.sentence(nb_words=4)
