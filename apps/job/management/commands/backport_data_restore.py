import gzip
import json
import os
import tempfile

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Restore data from backup with cleanup"

    def add_arguments(self, parser):
        parser.add_argument(
            "backup_file", type=str, help="Path to the backup JSON file"
        )
        parser.add_argument(
            "--skip-cleanup", action="store_true", help="Skip clearing existing data"
        )

    def handle(self, *args, **options):
        # Production safety check - absolutely prevent running in production
        if not settings.DEBUG:
            raise CommandError(
                "This command is DISABLED in production to prevent data loss. "
                "It would wipe your entire database. Use proper database restoration "
                "tools for production environments."
            )

        backup_file = options["backup_file"]
        skip_cleanup = options["skip_cleanup"]

        if not skip_cleanup:
            self.stdout.write("Clearing existing data...")
            call_command("flush", "--noinput")

            # Load essential company configuration
            self.stdout.write("Loading essential company configuration...")
            call_command("loaddata", "apps/workflow/fixtures/company_defaults.json")

        # Handle compressed files
        if backup_file.endswith(".gz"):
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False
            ) as temp_file:
                with gzip.open(backup_file, "rt", encoding="utf-8") as gz_file:
                    raw_data = gz_file.read()
                    json_data = json.loads(raw_data)

                    filtered_data = [
                        item
                        for item in json_data
                        if not (
                            item["model"] == "job.materialentry"
                            and (
                                item["fields"].get("purchase_order_line") is not None
                                or item["fields"].get("source_stock") is not None
                            )
                        )
                    ]

                    json.dump(filtered_data, temp_file, indent=2, ensure_ascii=False)
                temp_file_path = temp_file.name

            self.stdout.write(f"Loading data from {backup_file} (decompressed)...")
            try:
                call_command("loaddata", temp_file_path)
            finally:
                os.unlink(temp_file_path)
        else:
            self.stdout.write(f"Loading data from {backup_file}...")
            call_command("loaddata", backup_file)

        self.stdout.write("Running post-restore fixes...")
        self.post_restore_fixes()

    def post_restore_fixes(self):
        # Create dummy files for JobFile instances
        from apps.job.models import JobFile

        self.stdout.write("Creating dummy files for JobFile instances...")
        for job_file in JobFile.objects.filter(file_path__isnull=False).exclude(
            file_path=""
        ):
            dummy_path = os.path.join(settings.MEDIA_ROOT, str(job_file.file_path))
            os.makedirs(os.path.dirname(dummy_path), exist_ok=True)
            with open(dummy_path, "w") as f:
                f.write(f"Dummy file for JobFile {job_file.pk}\n")
                f.write(f"Original path: {job_file.file_path}\n")
            self.stdout.write(f"Created dummy file: {dummy_path}")

        # Create default admin if needed
        from apps.accounts.models import Staff

        self.stdout.write("Creating default admin user...")
        admin_user, created = Staff.objects.get_or_create(
            email="defaultadmin@example.com",
            defaults={
                "first_name": "Default",
                "last_name": "Admin",
                "preferred_name": None,
                "wage_rate": "40.00",
                "hours_mon": "8.0",
                "hours_tue": "8.0",
                "hours_wed": "8.0",
                "hours_thu": "8.0",
                "hours_fri": "8.0",
                "hours_sat": "0.00",
                "hours_sun": "0.00",
                "ims_payroll_id": "ADMIN-DEV",
                "is_active": True,
                "is_staff": True,
                "is_superuser": True,
                "password": "pbkdf2_sha256$870000$5Nw3RUuFaZZPCkeyVOm4kx$Attep1SqGF6ymdwm44LOte4wwszqte0W5ey3xcENFAI=",
                "date_joined": "2024-01-01T00:00:00Z",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            },
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS("Created defaultadmin@example.com user")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS("defaultadmin@example.com user already exists")
            )

        self.stdout.write(self.style.SUCCESS("Post-restore fixes completed"))
