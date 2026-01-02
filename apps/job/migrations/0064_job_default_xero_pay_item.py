"""Replace Job.payroll_category with Job.default_xero_pay_item.

This migration:
1. Removes the payroll_category FK (pointed to PayrollCategory)
2. Adds default_xero_pay_item FK to Job (points to XeroPayItem synced from Xero)
3. Adds xero_pay_item FK to CostLine (nullable - only for time entries)
4. Backfills all jobs: leave jobs get their specific type, work jobs get Ordinary Time
5. Backfills time CostLines with their job's default_xero_pay_item
"""

import django.db.models.deletion
from django.db import migrations, models


def backfill_default_xero_pay_item(apps, _schema_editor):
    """Set default_xero_pay_item for all jobs.

    - Rename "Other Leave" to "Bereavement Leave" (cleanup legacy name)
    - Leave jobs: Map to specific leave pay items by name
    - All other jobs: Set to Ordinary Time
    """
    Job = apps.get_model("job", "Job")
    XeroPayItem = apps.get_model("workflow", "XeroPayItem")

    # Shop client UUID - jobs with this client are "special" jobs
    SHOP_CLIENT_ID = "00000000-0000-0000-0000-000000000001"

    # Step 0: Rename "Other Leave" to "Bereavement Leave"
    renamed = Job.objects.filter(name="Other Leave").update(name="Bereavement Leave")
    if renamed:
        print(f"  Renamed {renamed} 'Other Leave' job(s) to 'Bereavement Leave'")

    # Get Ordinary Time - required for most jobs
    try:
        ordinary_time = XeroPayItem.objects.get(
            name="Ordinary Time", uses_leave_api=False
        )
    except XeroPayItem.DoesNotExist:
        raise RuntimeError(
            "'Ordinary Time' XeroPayItem not found. "
            "Run 'python manage.py xero --configure-payroll' to sync Xero pay items first."
        )

    # Step 1: Map leave jobs to their specific pay items
    # Keys are job names, values are XeroPayItem names
    leave_job_mappings = {
        "Annual Leave": "Annual Leave",
        "Sick Leave": "Sick Leave",
        "Unpaid Leave": "Unpaid Leave",
        "Bereavement Leave": "Bereavement Leave",
    }

    for job_name, pay_item_name in leave_job_mappings.items():
        try:
            pay_item = XeroPayItem.objects.get(name=pay_item_name)
        except XeroPayItem.DoesNotExist:
            print(
                f"  WARNING: XeroPayItem '{pay_item_name}' not found - skipping '{job_name}'"
            )
            continue

        count = Job.objects.filter(name=job_name).update(default_xero_pay_item=pay_item)
        if count:
            print(f"  Mapped '{job_name}' → '{pay_item_name}'")

    # Step 2: Set all remaining jobs to Ordinary Time
    remaining = Job.objects.filter(default_xero_pay_item__isnull=True)
    remaining_count = remaining.count()

    # List special jobs that will get Ordinary Time (for visibility)
    special_getting_ordinary = list(
        remaining.filter(client_id=SHOP_CLIENT_ID).values_list("name", flat=True)
    )
    if special_getting_ordinary:
        print(f"  Special jobs defaulting to Ordinary Time: {special_getting_ordinary}")

    remaining.update(default_xero_pay_item=ordinary_time)
    print(f"  Set {remaining_count} remaining jobs to 'Ordinary Time'")


def backfill_costline_xero_pay_item(apps, _schema_editor):
    """Set xero_pay_item for all time CostLines from their job's default."""
    CostLine = apps.get_model("job", "CostLine")

    time_entries = CostLine.objects.filter(
        kind="time", xero_pay_item__isnull=True
    ).select_related("cost_set__job")

    updated = 0
    for entry in time_entries:
        if entry.cost_set.job.default_xero_pay_item_id:
            entry.xero_pay_item_id = entry.cost_set.job.default_xero_pay_item_id
            entry.save(update_fields=["xero_pay_item_id"])
            updated += 1

    print(f"  Backfilled {updated} time CostLines")


def noop(_apps, _schema_editor):
    """Reverse operation - no-op since this is a one-way migration."""


class Migration(migrations.Migration):

    dependencies = [
        ("workflow", "0187_create_xero_pay_item"),
        ("job", "0063_job_payroll_category"),
    ]

    operations = [
        # Step 1: Remove old FK to PayrollCategory from historicaljob
        # Use SeparateDatabaseAndState because historicaljob uses custom table_name="workflow_historicaljob"
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="ALTER TABLE workflow_historicaljob DROP COLUMN IF EXISTS payroll_category_id;",
                    reverse_sql="ALTER TABLE workflow_historicaljob ADD COLUMN payroll_category_id CHAR(32) NULL;",
                ),
            ],
            state_operations=[
                migrations.RemoveField(
                    model_name="historicaljob",
                    name="payroll_category",
                ),
            ],
        ),
        migrations.RemoveField(
            model_name="job",
            name="payroll_category",
        ),
        # Step 2: Add new FK to XeroPayItem (nullable initially) to historicaljob
        # Use SeparateDatabaseAndState because historicaljob uses custom table_name="workflow_historicaljob"
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="ALTER TABLE workflow_historicaljob ADD COLUMN IF NOT EXISTS default_xero_pay_item_id CHAR(32) NULL;",
                    reverse_sql="ALTER TABLE workflow_historicaljob DROP COLUMN IF EXISTS default_xero_pay_item_id;",
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="historicaljob",
                    name="default_xero_pay_item",
                    field=models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        help_text="Default pay item for time entry.",
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="workflow.xeropayitem",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="job",
            name="default_xero_pay_item",
            field=models.ForeignKey(
                blank=True,
                help_text="Default pay item for time entry.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="jobs",
                to="workflow.xeropayitem",
            ),
        ),
        # Step 3: Backfill all jobs
        migrations.RunPython(backfill_default_xero_pay_item, noop),
        # Step 4: Add xero_pay_item FK to CostLine (nullable - only for time entries)
        migrations.AddField(
            model_name="costline",
            name="xero_pay_item",
            field=models.ForeignKey(
                blank=True,
                help_text="The Xero pay item for this time entry (leave type, earnings rate, etc.)",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="cost_lines",
                to="workflow.xeropayitem",
            ),
        ),
        # Step 5: Backfill time CostLines
        migrations.RunPython(backfill_costline_xero_pay_item, noop),
    ]
