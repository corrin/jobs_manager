"""Replace Job.payroll_category with Job.default_xero_pay_item.

This migration:
1. Removes the payroll_category FK (pointed to PayrollCategory)
2. Adds default_xero_pay_item FK (points to XeroPayItem synced from Xero)
3. Backfills all jobs: leave jobs get their specific type, work jobs get Ordinary Time
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
            "Run 'python manage.py setup_xero' to sync Xero pay items first."
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


def noop(_apps, _schema_editor):
    """Reverse operation - no-op since this is a one-way migration."""


class Migration(migrations.Migration):

    dependencies = [
        ("workflow", "0187_create_xero_pay_item"),
        ("job", "0061_job_payroll_category"),
    ]

    operations = [
        # Step 1: Remove old FK to PayrollCategory
        migrations.RemoveField(
            model_name="historicaljob",
            name="payroll_category",
        ),
        migrations.RemoveField(
            model_name="job",
            name="payroll_category",
        ),
        # Step 2: Add new FK to XeroPayItem (nullable initially)
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
    ]
