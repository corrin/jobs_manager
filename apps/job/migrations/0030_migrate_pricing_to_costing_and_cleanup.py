from decimal import Decimal

from django.db import migrations, transaction


def migrate_pricing_to_costing(apps, schema_editor):
    """
    Migrate JobPricing data to new CostSet/CostLine models and cleanup old data
    """
    # Get model classes
    JobPricing = apps.get_model("job", "JobPricing")
    CostSet = apps.get_model("job", "CostSet")
    CostLine = apps.get_model("job", "CostLine")

    # Get all JobPricing instances
    job_pricings = (
        JobPricing.objects.select_related("job")
        .prefetch_related("time_entries", "material_entries", "adjustment_entries")
        .order_by("id")
    )

    if not job_pricings.exists():
        print("No JobPricing instances found")
        return

    print(f"Processing {job_pricings.count()} JobPricing instances...")

    jobs_updated = set()
    cost_sets_created = 0
    cost_lines_created = 0

    for jp in job_pricings:
        try:
            with transaction.atomic():
                # Map pricing_methodology to kind
                stage_to_kind = {
                    "estimate": "estimate",
                    "quote": "quote",
                    "reality": "actual",
                }

                kind = stage_to_kind.get(jp.pricing_methodology)
                if not kind:
                    print(
                        f"Skipping JobPricing {jp.id} - unknown pricing_methodology: {jp.pricing_methodology}"
                    )
                    continue

                # Check if CostSet already exists for this combination
                rev = jp.revision_number or 1
                existing_cost_set = CostSet.objects.filter(
                    job=jp.job, kind=kind, rev=rev
                ).first()

                if existing_cost_set:
                    print(
                        f"Skipping JobPricing {jp.id} - CostSet already exists: {existing_cost_set}"
                    )
                    continue

                # Create CostSet
                cost_set = CostSet(
                    job=jp.job,
                    kind=kind,
                    rev=rev,
                    summary={},  # Will be updated after lines are created
                    created=jp.created_at,
                )
                cost_set.save()
                cost_sets_created += 1

                # Process time entries
                total_cost = Decimal("0.00")
                total_rev = Decimal("0.00")
                total_hours = Decimal("0.00")

                for time_entry in jp.time_entries.all():
                    # Get staff name safely
                    staff_name = "No staff"
                    staff_id = None
                    if hasattr(time_entry, "staff") and time_entry.staff:
                        staff_id = str(time_entry.staff.id)
                        if hasattr(time_entry.staff, "get_display_name"):
                            staff_name = time_entry.staff.get_display_name()
                        else:
                            staff_name = str(time_entry.staff)

                    cost_line = CostLine(
                        cost_set=cost_set,
                        kind="time",
                        desc=time_entry.description or f"Work - {staff_name}",
                        quantity=time_entry.hours,
                        unit_cost=time_entry.wage_rate
                        * time_entry.wage_rate_multiplier,
                        unit_rev=time_entry.charge_out_rate
                        * time_entry.wage_rate_multiplier,
                        ext_refs={"time_entry_id": str(time_entry.id)},
                        meta={
                            "staff_id": staff_id,
                            "date": time_entry.date.isoformat()
                            if time_entry.date
                            else None,
                            "is_billable": time_entry.is_billable,
                            "wage_rate_multiplier": float(
                                time_entry.wage_rate_multiplier
                            ),
                            "note": time_entry.note,
                        },
                    )
                    cost_line.save()
                    cost_lines_created += 1

                    total_cost += cost_line.total_cost
                    total_rev += cost_line.total_rev
                    total_hours += time_entry.hours

                # Process material entries
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
                    cost_line.save()
                    cost_lines_created += 1

                    total_cost += cost_line.total_cost
                    total_rev += cost_line.total_rev

                # Process adjustment entries
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
                cost_set.save()

                # Mark job for pointer updates
                jobs_updated.add(jp.job)

        except Exception as e:
            print(f"Error processing JobPricing {jp.id}: {str(e)}")
            raise

    # Update latest_* pointers on Jobs
    print("Updating latest_* pointers on Jobs...")
    for job in jobs_updated:
        for kind in ["estimate", "quote", "actual"]:
            cost_sets = CostSet.objects.filter(job=job, kind=kind).order_by("-rev")
            if cost_sets.count() == 1:
                # If exactly one CostSet exists, set the pointer
                cost_set = cost_sets.first()
                job.set_latest(kind, cost_set)

    print(f"Migration phase completed:")
    print(f"  - {cost_sets_created} CostSets created")
    print(f"  - {cost_lines_created} CostLines created")
    print(f"  - {len(jobs_updated)} Jobs affected")

    # Cleanup phase - delete old data
    print("Starting cleanup phase...")

    # Get models for cleanup
    TimeEntry = apps.get_model("timesheet", "TimeEntry")
    MaterialEntry = apps.get_model("job", "MaterialEntry")
    AdjustmentEntry = apps.get_model("job", "AdjustmentEntry")
    Job = apps.get_model("job", "Job")
    JobPart = apps.get_model("job", "JobPart")

    # Count entries before deletion
    time_entries_count = TimeEntry.objects.count()
    material_entries_count = MaterialEntry.objects.count()
    adjustment_entries_count = AdjustmentEntry.objects.count()
    job_pricings_count = JobPricing.objects.count()

    # First, clear all foreign keys that point to JobPricing
    print("Clearing Job foreign key references to JobPricing...")
    Job.objects.update(
        latest_estimate_pricing=None,
        latest_quote_pricing=None,
        latest_reality_pricing=None,
    )

    print("Clearing JobPart foreign key references to JobPricing...")
    JobPart.objects.update(job_pricing=None)

    # Delete using raw SQL to avoid ORM ordering issues
    from django.db import connection

    with connection.cursor() as cursor:
        # Delete related entries first
        cursor.execute("DELETE FROM workflow_timeentry")
        cursor.execute("DELETE FROM workflow_materialentry")
        cursor.execute("DELETE FROM workflow_adjustmententry")

        # Finally delete JobPricing instances (now that Job FKs are cleared)
        cursor.execute("DELETE FROM workflow_jobpricing")

    print(f"Cleanup completed:")
    print(f"  - Job and JobPart foreign key references cleared")
    print(f"  - {time_entries_count} TimeEntries deleted")
    print(f"  - {material_entries_count} MaterialEntries deleted")
    print(f"  - {adjustment_entries_count} AdjustmentEntries deleted")
    print(f"  - {job_pricings_count} JobPricings deleted")


def reverse_migration(apps, schema_editor):
    """
    Reverse migration - this cannot be safely reversed as we deleted the original data
    """
    raise RuntimeError(
        "This migration cannot be reversed as it deletes the original JobPricing data. "
        "You would need to restore from a backup."
    )


class Migration(migrations.Migration):
    dependencies = [
        ("job", "0029_remove_historicaljob_contact_email_and_more"),
        ("timesheet", "0002_alter_timeentry_job_pricing_fk"),
    ]

    operations = [
        migrations.RunPython(
            migrate_pricing_to_costing,
            reverse_migration,
            hints={"target_db": "default"},
        ),
    ]
