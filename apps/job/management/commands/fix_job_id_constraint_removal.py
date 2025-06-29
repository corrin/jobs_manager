from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Removes the job_id constraint and column from workflow_jobpart table"

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # Disable foreign key checks
            self.stdout.write("Disabling foreign key checks...")
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")

            try:
                # Try to drop the constraint
                constraint_name = "workflow_jobpart_job_id_ec85d899_fk_workflow_job_id"
                self.stdout.write(f"Removing constraint {constraint_name}...")

                if connection.vendor == "mysql":
                    cursor.execute(
                        f"ALTER TABLE workflow_jobpart DROP FOREIGN KEY {constraint_name};"
                    )
                elif connection.vendor == "postgresql":
                    cursor.execute(
                        f"ALTER TABLE workflow_jobpart DROP CONSTRAINT {constraint_name};"
                    )
                elif connection.vendor == "sqlite":
                    self.stdout.write(
                        self.style.WARNING(
                            "SQLite handles constraints differently, proceeding with column removal"
                        )
                    )

                # Drop the column
                self.stdout.write(
                    "Removing column job_id from workflow_jobpart...")
                cursor.execute(
                    "ALTER TABLE workflow_jobpart DROP COLUMN job_id;")

                self.stdout.write(
                    self.style.SUCCESS(
                        "Successfully removed job_id constraint and column"
                    )
                )

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))
                raise

            finally:
                # Re-enable foreign key checks
                self.stdout.write("Re-enabling foreign key checks...")
                cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
