from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.job.enums import JobPricingStage
from apps.job.models import CostLine, CostSet, JobPricing

try:
    from tqdm import tqdm

    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False


class Command(BaseCommand):
    help = "Migrate JobPricing data to new CostSet/CostLine models"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run without saving to database",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        if dry_run:
            self.stdout.write(
                self.style.WARNING("Running in DRY RUN mode - no changes will be saved")
            )

        # Get all JobPricing instances
        job_pricings = (
            JobPricing.objects.select_related("job")
            .prefetch_related(
                "time_entries__staff", "material_entries", "adjustment_entries"
            )
            .all()
        )

        if not job_pricings.exists():
            self.stdout.write(self.style.WARNING("No JobPricing instances found"))
            return

        # Progress bar if tqdm is available
        if HAS_TQDM:
            job_pricings_iter = tqdm(job_pricings, desc="Migrating JobPricing")
        else:
            job_pricings_iter = job_pricings
            self.stdout.write(
                f"Processing {job_pricings.count()} JobPricing instances..."
            )

        jobs_updated = set()
        cost_sets_created = 0
        cost_lines_created = 0

        for jp in job_pricings_iter:
            try:
                with transaction.atomic():
                    # Map pricing_stage to kind
                    stage_to_kind = {
                        JobPricingStage.ESTIMATE: "estimate",
                        JobPricingStage.QUOTE: "quote",
                        JobPricingStage.REALITY: "actual",
                    }

                    kind = stage_to_kind.get(jp.pricing_stage)
                    if not kind:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Skipping JobPricing {jp.id} - unknown pricing_stage: {jp.pricing_stage}"
                            )
                        )
                        continue

                    # Check if CostSet already exists for this combination
                    rev = jp.revision_number or 1
                    existing_cost_set = CostSet.objects.filter(
                        job=jp.job, kind=kind, rev=rev
                    ).first()

                    if existing_cost_set:
                        if not HAS_TQDM:
                            self.stdout.write(
                                f"Skipping JobPricing {jp.id} - CostSet already exists: {existing_cost_set}"
                            )
                        continue  # Create CostSet
                    cost_set = CostSet(
                        job=jp.job,
                        kind=kind,
                        rev=rev,
                        summary={},  # Will be updated after lines are created
                        created=jp.created_at,
                    )

                    if not dry_run:
                        cost_set.save()
                    cost_sets_created += 1  # Process time entries
                    total_cost = Decimal("0.00")
                    total_rev = Decimal("0.00")
                    total_hours = Decimal("0.00")

                    for time_entry in jp.time_entries.all():
                        cost_line = CostLine(
                            cost_set=cost_set,
                            kind="time",
                            desc=time_entry.description
                            or f"Work - {time_entry.staff.get_display_name() if time_entry.staff else 'No staff'}",
                            quantity=time_entry.hours,
                            unit_cost=time_entry.wage_rate
                            * time_entry.wage_rate_multiplier,
                            unit_rev=time_entry.charge_out_rate
                            * time_entry.wage_rate_multiplier,
                            ext_refs={"time_entry_id": str(time_entry.id)},
                            meta={
                                "staff_id": (
                                    str(time_entry.staff.id)
                                    if time_entry.staff
                                    else None
                                ),
                                "date": (
                                    time_entry.date.isoformat()
                                    if time_entry.date
                                    else None
                                ),
                                "is_billable": time_entry.is_billable,
                                "wage_rate_multiplier": float(
                                    time_entry.wage_rate_multiplier
                                ),
                                "note": time_entry.note,
                            },
                        )

                        if not dry_run:
                            cost_line.save()
                        cost_lines_created += 1

                        total_cost += cost_line.total_cost
                        total_rev += cost_line.total_rev
                        total_hours += time_entry.hours  # Process material entries
                    for material_entry in jp.material_entries.all():
                        cost_line = CostLine(
                            cost_set=cost_set,
                            kind="material",
                            desc=material_entry.description
                            or f"Material - {material_entry.item_code}",
                            quantity=material_entry.quantity,
                            unit_cost=material_entry.unit_cost,
                            unit_rev=material_entry.unit_revenue,
                            ext_refs={"material_entry_id": str(material_entry.id)},
                            meta={
                                "item_code": material_entry.item_code,
                                "comments": material_entry.comments,
                            },
                        )

                        if not dry_run:
                            cost_line.save()
                        cost_lines_created += 1

                        total_cost += cost_line.total_cost
                        total_rev += cost_line.total_rev  # Process adjustment entries
                    for adjustment_entry in jp.adjustment_entries.all():
                        cost_line = CostLine(
                            cost_set=cost_set,
                            kind="adjust",
                            desc=adjustment_entry.description or "Adjustment",
                            quantity=Decimal("1.000"),
                            unit_cost=adjustment_entry.cost_adjustment,
                            unit_rev=adjustment_entry.price_adjustment,
                            ext_refs={"adjustment_entry_id": str(adjustment_entry.id)},
                            meta={
                                "comments": adjustment_entry.comments,
                            },
                        )

                        if not dry_run:
                            cost_line.save()
                        cost_lines_created += 1
                        total_cost += cost_line.total_cost
                        total_rev += cost_line.total_rev

                    # Update CostSet summary
                    cost_set.summary = {
                        "cost": float(total_cost),
                        "rev": float(total_rev),
                        "hours": float(total_hours),
                    }

                    if not dry_run:
                        cost_set.save()

                    # Mark job for pointer updates
                    jobs_updated.add(jp.job)

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error processing JobPricing {jp.id}: {str(e)}")
                )
                if not dry_run:
                    raise  # Update latest_* pointers on Jobs
        if not dry_run:
            self.stdout.write("Updating latest_* pointers on Jobs...")

            jobs_to_update = list(jobs_updated)
            if HAS_TQDM:
                jobs_iter = tqdm(jobs_to_update, desc="Updating pointers")
            else:
                jobs_iter = jobs_to_update

            for job in jobs_iter:
                for kind in ["estimate", "quote", "actual"]:
                    cost_sets = CostSet.objects.filter(job=job, kind=kind).order_by(
                        "-rev"
                    )
                    if cost_sets.count() == 1:
                        # If exactly one CostSet exists, set the pointer
                        cost_set = cost_sets.first()
                        job.set_latest(kind, cost_set)

        # Final report
        self.stdout.write(
            self.style.SUCCESS(
                f"\n{'DRY RUN - ' if dry_run else ''}Migration completed:"
            )
        )
        self.stdout.write(f"  - {cost_sets_created} CostSets created")
        self.stdout.write(f"  - {cost_lines_created} CostLines created")
        self.stdout.write(f"  - {len(jobs_updated)} Jobs affected")

        if dry_run:
            self.stdout.write(
                self.style.WARNING("Run again without --dry-run to apply changes")
            )
