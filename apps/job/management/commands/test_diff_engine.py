"""
Test command for CostSet diff engine

Tests the diff functionality with sample data to verify it works correctly.
"""

from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.job.diff import apply_diff, diff_costset
from apps.job.importers.draft import DraftLine
from apps.job.models import CostLine, CostSet, Job


class Command(BaseCommand):
    help = "Test the CostSet diff engine with sample data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--job-id", type=int, help="Job ID to test with (will create test cost set)"
        )
        parser.add_argument(
            "--verbose", action="store_true", help="Show detailed output"
        )

    def handle(self, *args, **options):
        job_id = options.get("job_id")
        verbose = options.get("verbose", False)

        # Get or create test job
        if job_id:
            try:
                job = Job.objects.get(id=job_id)
                self.stdout.write(f"Using existing job: {job}")
            except Job.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Job {job_id} not found"))
                return
        else:
            # Create a test job for demonstration
            job, created = Job.objects.get_or_create(
                name="Test Diff Job",
                defaults={
                    "description": "Test job for diff engine",
                    "job_number": 9999,
                },
            )
            if created:
                self.stdout.write(f"Created test job: {job}")
            else:
                self.stdout.write(f"Using existing test job: {job}")

        # Create initial CostSet with some test data
        old_cost_set = self._create_test_cost_set(job)
        self.stdout.write(f"Created test CostSet: {old_cost_set}")

        if verbose:
            self._show_cost_set_details(old_cost_set, "Original CostSet")

        # Create modified DraftLines (simulating new import)
        draft_lines = self._create_test_draft_lines()
        self.stdout.write(f"Created {len(draft_lines)} test DraftLines")

        if verbose:
            self._show_draft_lines(draft_lines)

        # Run diff
        diff_result = diff_costset(old_cost_set, draft_lines)

        # Show diff results
        self.stdout.write("\n📊 Diff Results:")
        self.stdout.write(f"  Additions: {len(diff_result.to_add)}")
        self.stdout.write(f"  Updates: {len(diff_result.to_update)}")
        self.stdout.write(f"  Deletions: {len(diff_result.to_delete)}")
        self.stdout.write(f"  Total changes: {diff_result.summary['total_changes']}")

        if verbose:
            self._show_diff_details(diff_result)

        # Apply diff to create new cost set
        if diff_result.has_changes:
            new_cost_set = apply_diff(old_cost_set, diff_result)
            self.stdout.write(f"\n✅ Applied diff - created new CostSet: {new_cost_set}")

            if verbose:
                self._show_cost_set_details(new_cost_set, "New CostSet")
        else:
            self.stdout.write("\n✅ No changes detected - no new CostSet created")

        self.stdout.write(
            self.style.SUCCESS("\n🎉 Diff engine test completed successfully")
        )

    def _create_test_cost_set(self, job: Job) -> CostSet:
        """Create a test CostSet with sample data"""
        # Check if there's already a test CostSet for this job
        existing_cost_set = (
            CostSet.objects.filter(job=job, kind="estimate").order_by("-rev").first()
        )

        if existing_cost_set:
            # Delete all existing CostSets for this job to start fresh
            CostSet.objects.filter(job=job, kind="estimate").delete()
            self.stdout.write(f"Cleaned up existing CostSets for job {job.id}")

        cost_set = CostSet.objects.create(
            job=job, kind="estimate", rev=1, summary={"cost": 0, "rev": 0, "hours": 0}
        )

        # Add some test cost lines
        test_lines = [
            {
                "kind": "time",
                "desc": "assembly - Labour",
                "quantity": Decimal("16.00"),
                "unit_cost": Decimal("32.00"),
                "unit_rev": Decimal("110.00"),
                "ext_refs": {"source_row": "1"},
            },
            {
                "kind": "material",
                "desc": 'brass tube 50.8 (2") - Materials',
                "quantity": Decimal("2.00"),
                "unit_cost": Decimal("389.50"),
                "unit_rev": Decimal("467.40"),
                "ext_refs": {"source_row": "2"},
            },
            {
                "kind": "material",
                "desc": "old material - Materials",
                "quantity": Decimal("1.00"),
                "unit_cost": Decimal("100.00"),
                "unit_rev": Decimal("120.00"),
                "ext_refs": {"source_row": "10"},
            },
        ]

        for line_data in test_lines:
            CostLine.objects.create(cost_set=cost_set, **line_data)

        # Update summary
        cost_lines = cost_set.cost_lines.all()
        total_cost = sum(line.total_cost for line in cost_lines)
        total_rev = sum(line.total_rev for line in cost_lines)
        total_hours = sum(
            float(line.quantity) for line in cost_lines if line.kind == "time"
        )

        cost_set.summary = {
            "cost": float(total_cost),
            "rev": float(total_rev),
            "hours": total_hours,
        }
        cost_set.save()

        return cost_set

    def _create_test_draft_lines(self) -> list[DraftLine]:
        """Create test DraftLines that simulate import results"""
        return [
            # Existing line - no change
            DraftLine(
                kind="time",
                desc="assembly - Labour",
                quantity=Decimal("16.00"),
                unit_cost=Decimal("32.00"),
                unit_rev=Decimal("110.00"),
                source_row=1,
            ),
            # Existing line - updated quantity
            DraftLine(
                kind="material",
                desc='brass tube 50.8 (2") - Materials',
                quantity=Decimal("3.00"),  # Changed from 2.00
                unit_cost=Decimal("389.50"),
                unit_rev=Decimal("467.40"),
                source_row=2,
            ),
            # New line
            DraftLine(
                kind="material",
                desc="brass caps 732 - Materials",
                quantity=Decimal("6.00"),
                unit_cost=Decimal("53.95"),
                unit_rev=Decimal("64.74"),
                source_row=3,
            ),
            # Another new line
            DraftLine(
                kind="time",
                desc="site visit - Labour",
                quantity=Decimal("4.00"),
                unit_cost=Decimal("32.00"),
                unit_rev=Decimal("110.00"),
                source_row=8,
            ),
            # Note: 'old material' line is missing - should be deleted
        ]

    def _show_cost_set_details(self, cost_set: CostSet, title: str):
        """Show detailed information about a CostSet"""
        self.stdout.write(f"\n📋 {title}:")
        self.stdout.write(f"  ID: {cost_set.id}")
        self.stdout.write(f"  Kind: {cost_set.kind}")
        self.stdout.write(f"  Revision: {cost_set.rev}")
        self.stdout.write(f"  Summary: {cost_set.summary}")

        lines = cost_set.cost_lines.all()
        self.stdout.write(f"  Lines ({len(lines)}):")
        for i, line in enumerate(lines, 1):
            self.stdout.write(
                f"    {i}. [{line.kind}] {line.desc} "
                f"qty={line.quantity} cost=${line.unit_cost} rev=${line.unit_rev}"
            )

    def _show_draft_lines(self, drafts: list[DraftLine]):
        """Show draft line details"""
        self.stdout.write("\n📝 Draft Lines:")
        for i, draft in enumerate(drafts, 1):
            self.stdout.write(
                f"  {i}. [{draft.kind}] {draft.desc} "
                f"qty={draft.quantity} cost=${draft.unit_cost} rev=${draft.unit_rev} "
                f"(row {draft.source_row})"
            )

    def _show_diff_details(self, diff_result):
        """Show detailed diff results"""
        if diff_result.to_add:
            self.stdout.write(f"\n➕ Lines to ADD ({len(diff_result.to_add)}):")
            for i, draft in enumerate(diff_result.to_add, 1):
                self.stdout.write(
                    f"  {i}. [{draft.kind}] {draft.desc} "
                    f"qty={draft.quantity} cost=${draft.unit_cost} rev=${draft.unit_rev}"
                )

        if diff_result.to_update:
            self.stdout.write(f"\n🔄 Lines to UPDATE ({len(diff_result.to_update)}):")
            for i, (old_line, draft) in enumerate(diff_result.to_update, 1):
                self.stdout.write(f"  {i}. [{old_line.kind}] {old_line.desc}")
                self.stdout.write(
                    f"     OLD: qty={old_line.quantity} cost=${old_line.unit_cost} rev=${old_line.unit_rev}"
                )
                self.stdout.write(
                    f"     NEW: qty={draft.quantity} cost=${draft.unit_cost} rev=${draft.unit_rev}"
                )

        if diff_result.to_delete:
            self.stdout.write(f"\n❌ Lines to DELETE ({len(diff_result.to_delete)}):")
            for i, line in enumerate(diff_result.to_delete, 1):
                self.stdout.write(
                    f"  {i}. [{line.kind}] {line.desc} "
                    f"qty={line.quantity} cost=${line.unit_cost} rev=${line.unit_rev}"
                )
