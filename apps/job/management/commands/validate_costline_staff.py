import logging
from typing import Dict, List, Optional
from uuid import UUID

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import Staff
from apps.job.models.costing import CostLine

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Validates time cost lines for staff references and optionally reassigns "
        "invalid entries to a known staff member."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--job-id",
            dest="job_id",
            type=str,
            help="Restrict validation to a single job UUID.",
        )
        parser.add_argument(
            "--limit",
            dest="limit",
            type=int,
            default=50,
            help="Maximum number of invalid entries to print (default: 50).",
        )
        parser.add_argument(
            "--assign-staff-id",
            dest="assign_staff_id",
            type=str,
            help=(
                "UUID of the staff member that should replace invalid/missing "
                "staff references."
            ),
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            dest="apply",
            help="Persist fixes instead of running in dry-run mode.",
        )

    def handle(self, *args, **options):
        job_id = self._parse_uuid(options.get("job_id"), "job-id", allow_none=True)
        limit = max(1, options.get("limit") or 50)
        assign_staff_id = self._parse_uuid(
            options.get("assign_staff_id"), "assign-staff-id", allow_none=True
        )
        apply_changes = options.get("apply", False)

        if apply_changes and not assign_staff_id:
            raise CommandError(
                "The --apply flag requires --assign-staff-id to be provided."
            )

        invalid_entries = self._collect_invalid_cost_lines(job_id=job_id)
        total_invalid = len(invalid_entries)
        self.stdout.write(
            self.style.WARNING(f"Detected {total_invalid} invalid time cost line(s).")
        )

        if not invalid_entries:
            self.stdout.write(self.style.SUCCESS("No action required."))
            return

        self._print_sample(invalid_entries, limit)

        if not assign_staff_id:
            self.stdout.write(
                self.style.NOTICE(
                    "Run again with --assign-staff-id <uuid> to fix invalid entries."
                )
            )
            return

        staff = self._get_staff(assign_staff_id)
        if not apply_changes:
            self.stdout.write(
                self.style.WARNING(
                    f"Dry run: {total_invalid} cost line(s) would be reassigned to "
                    f"{staff.get_display_full_name()} ({staff.id}). "
                    "Use --apply to persist changes."
                )
            )
            return

        updated_count = self._reassign_cost_lines(invalid_entries, staff)
        self.stdout.write(
            self.style.SUCCESS(
                f"Reassigned {updated_count} cost line(s) to "
                f"{staff.get_display_full_name()} ({staff.id})."
            )
        )

    def _collect_invalid_cost_lines(
        self, job_id: Optional[UUID] = None
    ) -> List[Dict[str, object]]:
        queryset = (
            CostLine.objects.filter(kind="time")
            .select_related("cost_set__job")
            .order_by("created_at")
        )
        if job_id:
            queryset = queryset.filter(cost_set__job_id=job_id)

        staff_cache: Dict[str, bool] = {}
        invalid_entries: List[Dict[str, object]] = []

        for line in queryset.iterator(chunk_size=500):
            reason = self._get_invalid_reason(line, staff_cache)
            if not reason:
                continue

            invalid_entries.append(
                {
                    "line": line,
                    "reason": reason,
                    "job_number": line.cost_set.job.job_number,
                    "job_name": line.cost_set.job.name,
                    "staff_id": line.meta.get("staff_id"),
                }
            )

        return invalid_entries

    def _get_invalid_reason(
        self, line: CostLine, staff_cache: Dict[str, bool]
    ) -> Optional[str]:
        meta = line.meta or {}
        staff_id = meta.get("staff_id")

        if not staff_id:
            return "missing_staff_id"

        try:
            normalized_staff_id = str(UUID(str(staff_id)))
        except (ValueError, TypeError):
            return "invalid_staff_uuid"

        if normalized_staff_id not in staff_cache:
            staff_cache[normalized_staff_id] = Staff.objects.filter(
                id=normalized_staff_id
            ).exists()

        if not staff_cache[normalized_staff_id]:
            return "staff_not_found"

        return None

    def _print_sample(self, invalid_entries: List[Dict[str, object]], limit: int):
        self.stdout.write(self.style.HTTP_INFO("Sample invalid entries:"))
        for entry in invalid_entries[:limit]:
            self.stdout.write(
                f"- Job {entry['job_number']} ({entry['job_name']}) "
                f"CostLine {entry['line'].id}: reason={entry['reason']} "
                f"staff_id={entry['staff_id']}"
            )

        if len(invalid_entries) > limit:
            self.stdout.write(
                self.style.WARNING(
                    f"... truncated output. Re-run with --limit {len(invalid_entries)} "
                    "to display all entries."
                )
            )

    def _reassign_cost_lines(
        self, invalid_entries: List[Dict[str, object]], staff: Staff
    ) -> int:
        updated = 0
        with transaction.atomic():
            for entry in invalid_entries:
                line: CostLine = entry["line"]  # type: ignore[assignment]
                meta = dict(line.meta or {})
                meta["staff_id"] = str(staff.id)
                line.meta = meta
                line.save(update_fields=["meta", "updated_at"])
                updated += 1

        logger.info(
            "Reassigned %s invalid cost line(s) to staff_id=%s",
            updated,
            staff.id,
        )
        return updated

    def _parse_uuid(
        self, raw_value: Optional[str], flag_name: str, allow_none: bool = False
    ) -> Optional[UUID]:
        if not raw_value:
            if allow_none:
                return None
            raise CommandError(f"--{flag_name} is required.")
        try:
            return UUID(str(raw_value))
        except (ValueError, TypeError) as exc:
            raise CommandError(
                f"Invalid UUID supplied for --{flag_name}: {raw_value}"
            ) from exc

    def _get_staff(self, staff_id: UUID) -> Staff:
        try:
            return Staff.objects.get(id=staff_id)
        except Staff.DoesNotExist as exc:
            raise CommandError(f"Staff with id {staff_id} does not exist.") from exc
