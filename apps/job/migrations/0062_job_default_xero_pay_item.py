"""Replace Job.payroll_category with Job.default_xero_pay_item.

This migration:
1. Removes the payroll_category FK (pointed to PayrollCategory)
2. Adds default_xero_pay_item FK (points to XeroPayItem synced from Xero)
3. Backfills leave jobs by matching job name to XeroPayItem.name
"""

import django.db.models.deletion
from django.db import migrations, models


def backfill_default_xero_pay_item(apps, schema_editor):
    """Set default_xero_pay_item for leave jobs by matching job name to XeroPayItem.name."""
    Job = apps.get_model("job", "Job")
    XeroPayItem = apps.get_model("workflow", "XeroPayItem")

    # Map job name patterns to XeroPayItem names
    leave_mappings = {
        "annual leave": "Annual Leave",
        "sick leave": "Sick Leave",
        "bereavement leave": "Bereavement Leave",
        "unpaid leave": "Unpaid Leave",
    }

    for pattern, xero_name in leave_mappings.items():
        try:
            pay_item = XeroPayItem.objects.get(name=xero_name)
        except XeroPayItem.DoesNotExist:
            print(f"  WARNING: XeroPayItem '{xero_name}' not found - skipping")
            continue

        # Find jobs matching this pattern (case-insensitive)
        matching_jobs = Job.objects.filter(name__icontains=pattern)
        count = matching_jobs.update(default_xero_pay_item=pay_item)
        if count:
            print(f"  Set default_xero_pay_item for {count} jobs matching '{pattern}'")


def noop(apps, schema_editor):
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
        # Step 2: Add new FK to XeroPayItem
        migrations.AddField(
            model_name="historicaljob",
            name="default_xero_pay_item",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                help_text="XeroPayItem for leave jobs. NULL for regular work jobs.",
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
                help_text="XeroPayItem for leave jobs. NULL for regular work jobs.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="jobs",
                to="workflow.xeropayitem",
            ),
        ),
        # Step 3: Backfill leave jobs
        migrations.RunPython(backfill_default_xero_pay_item, noop),
    ]
