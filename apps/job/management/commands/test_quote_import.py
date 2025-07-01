"""
Test Quote Import Service

Command to test the complete quote import service functionality.
"""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.job.models import Job
from apps.job.services.import_quote_service import (
    QuoteImportError,
    import_quote_from_file,
    preview_quote_import,
)


class Command(BaseCommand):
    help = "Test the quote import service with the test spreadsheet"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default="Quoting Spreadsheet 2025.xlsx",
            help="Path to the Excel file (default: Quoting Spreadsheet 2025.xlsx in project root)",
        )
        parser.add_argument(
            "--job-id",
            type=str,
            help="Job ID to import quote for (if not provided, will use or create test job)",
        )
        parser.add_argument(
            "--preview-only",
            action="store_true",
            help="Only preview import, do not actually import",
        )
        parser.add_argument(
            "--skip-validation",
            action="store_true",
            help="Skip spreadsheet validation during import",
        )

    def handle(self, *args, **options):
        # Determine the file path
        file_path = options["file"]
        if not Path(file_path).is_absolute():
            # If relative path, assume it's from project root
            from django.conf import settings

            project_root = Path(settings.BASE_DIR)
            file_path = project_root / file_path

        file_path = Path(file_path)

        self.stdout.write(f"Testing quote import service with: {file_path}")

        # Check if file exists
        if not file_path.exists():
            raise CommandError(f"Spreadsheet not found at {file_path}")

        # Get or create test job
        if options["job_id"]:
            try:
                job = Job.objects.get(pk=options["job_id"])
                self.stdout.write(
                    f"Using existing job: [Job {job.job_number}] {job.name}"
                )
            except Job.DoesNotExist:
                raise CommandError(f"Job with ID {options['job_id']} not found")
        else:
            job = self._get_or_create_test_job()
            self.stdout.write(f"Using test job: [Job {job.job_number}] {job.name}")

        try:
            if options["preview_only"]:
                # Preview only
                self.stdout.write(
                    self.style.WARNING(
                        "Preview mode - no actual import will be performed"
                    )
                )
                self._test_preview(job, str(file_path))
            else:
                # Full import test
                self._test_import(job, str(file_path), options["skip_validation"])

        except QuoteImportError as e:
            raise CommandError(f"Quote import error: {e}")
        except Exception as e:
            raise CommandError(f"Unexpected error: {e}")

    def _get_or_create_test_job(self) -> Job:
        """Get or create a test job for quote import testing"""
        # Try to find existing test job
        test_job = Job.objects.filter(name__icontains="Quote Import Test").first()

        if test_job:
            return test_job

        # Create new test job
        from apps.client.models import Client

        # Get first available client or create one
        client = Client.objects.first()
        if not client:
            self.stdout.write("Creating test client...")
            client = Client.objects.create(name="Test Client", account_ref="TEST001")

        test_job = Job.objects.create(
            name="Quote Import Test Job",
            client=client,
            status="quoting",
            description="Test job for quote import service testing",
        )

        self.stdout.write(
            f"Created test job: [Job {test_job.job_number}] {test_job.name}"
        )
        return test_job

    def _test_preview(self, job: Job, file_path: str):
        """Test the preview functionality"""
        self.stdout.write("\n🔍 Testing quote import preview...")

        preview_data = preview_quote_import(job, file_path)

        self.stdout.write("\n📋 Preview Results:")
        self.stdout.write(f"  Can proceed: {preview_data.get('can_proceed', False)}")
        # Show validation report
        validation_report = preview_data.get("validation_report")
        if validation_report:
            self.stdout.write(
                f"  Validation issues: {validation_report.get('summary', {}).get('total_issues', 0)}"
            )
            if validation_report.get("critical_issues"):
                self.stdout.write(
                    f"    🚨 Critical: {len(validation_report['critical_issues'])}"
                )
            if validation_report.get("errors"):
                self.stdout.write(f"    ❌ Errors: {len(validation_report['errors'])}")
            if validation_report.get("warnings"):
                self.stdout.write(
                    f"    ⚠️ Warnings: {len(validation_report['warnings'])}"
                )

        # Show draft lines count
        draft_lines = preview_data.get("draft_lines", [])
        self.stdout.write(f"  Draft lines found: {len(draft_lines)}")

        # Show diff preview
        diff_preview = preview_data.get("diff_preview")
        if diff_preview:
            self.stdout.write(f"  Next revision: {diff_preview['next_revision']}")
            self.stdout.write(f"  Total changes: {diff_preview['total_changes']}")
            self.stdout.write(f"    ➕ Additions: {diff_preview['additions_count']}")
            self.stdout.write(f"    🔄 Updates: {diff_preview['updates_count']}")
            self.stdout.write(f"    ❌ Deletions: {diff_preview['deletions_count']}")

        if preview_data.get("can_proceed", False):
            self.stdout.write(
                self.style.SUCCESS("\n✅ Preview successful - import can proceed")
            )
        else:
            self.stdout.write(
                self.style.ERROR("\n❌ Preview failed - import cannot proceed")
            )

    def _test_import(self, job: Job, file_path: str, skip_validation: bool):
        """Test the full import functionality"""
        self.stdout.write(
            f"\n📥 Testing quote import (skip_validation={skip_validation})..."
        )

        # Show current state
        current_quote = job.get_latest("quote")
        if current_quote:
            self.stdout.write(
                f"Current quote: Rev {current_quote.rev} (ID: {current_quote.id})"
            )
        else:
            self.stdout.write("No current quote found")

        # Perform import
        result = import_quote_from_file(job, file_path, skip_validation=skip_validation)

        # Show results
        if result.success:
            self.stdout.write(self.style.SUCCESS("\n✅ Quote import successful!"))

            if result.cost_set:
                self.stdout.write(
                    f"  New CostSet: Rev {result.cost_set.rev} (ID: {result.cost_set.id})"
                )
                self.stdout.write(f"  Summary: {result.cost_set.summary}")
                self.stdout.write(f"  Cost lines: {result.cost_set.cost_lines.count()}")

            if result.diff_result:
                self.stdout.write("  Changes applied:")
                self.stdout.write(
                    f"    ➕ Added: {len(result.diff_result.to_add)} lines"
                )
                self.stdout.write(
                    f"    🔄 Updated: {len(result.diff_result.to_update)} lines"
                )
                self.stdout.write(
                    f"    ❌ Deleted: {len(result.diff_result.to_delete)} lines"
                )

            # Verify job pointer was updated
            updated_job = Job.objects.get(pk=job.pk)
            latest_quote = updated_job.get_latest("quote")
            if latest_quote and latest_quote.id == result.cost_set.id:
                self.stdout.write("  ✅ Job latest_quote pointer updated correctly")
            else:
                self.stdout.write("  ❌ Job latest_quote pointer not updated correctly")

        else:
            self.stdout.write(self.style.ERROR("\n❌ Quote import failed!"))
            self.stdout.write(f"  Error: {result.error_message}")
            if result.validation_report:
                self.stdout.write("  Validation issues:")
                for issue in result.validation_report.get("critical_issues", []):
                    self.stdout.write(f"    🚨 CRITICAL: {issue.get('message', issue)}")
                for issue in result.validation_report.get("errors", []):
                    self.stdout.write(f"    ❌ ERROR: {issue.get('message', issue)}")
