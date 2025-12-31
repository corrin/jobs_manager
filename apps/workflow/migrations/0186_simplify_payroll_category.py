"""
Simplify PayrollCategory model:
1. Add xero_name field
2. Migrate data from old fields to xero_name
3. Set payroll_category FK on leave jobs
4. Remove old fields (name, display_name, job_name_pattern, xero_leave_type_name, xero_earnings_rate_name)
"""

from django.db import migrations, models


def migrate_xero_names_forward(apps, schema_editor):
    """Populate xero_name from existing fields."""
    PayrollCategory = apps.get_model("workflow", "PayrollCategory")

    for category in PayrollCategory.objects.all():
        # For leave categories, use xero_leave_type_name or display_name
        # For work categories, use xero_earnings_rate_name or display_name
        if category.uses_leave_api:
            category.xero_name = (
                category.xero_leave_type_name or category.display_name or category.name
            )
        else:
            category.xero_name = (
                category.xero_earnings_rate_name
                or category.display_name
                or category.name
            )
        category.save()


def set_job_payroll_categories_forward(apps, schema_editor):
    """Set payroll_category FK on leave jobs based on job name pattern matching."""
    Job = apps.get_model("job", "Job")
    PayrollCategory = apps.get_model("workflow", "PayrollCategory")

    # Map job names to PayrollCategory xero_names
    leave_mappings = {
        "annual leave": "Annual Leave",
        "sick leave": "Sick Leave",
        "bereavement leave": "Bereavement Leave",
        "unpaid leave": "Unpaid Leave",
    }

    for pattern, xero_name in leave_mappings.items():
        try:
            category = PayrollCategory.objects.get(xero_name=xero_name)
        except PayrollCategory.DoesNotExist:
            continue

        # Find jobs matching this pattern (case-insensitive)
        matching_jobs = Job.objects.filter(name__icontains=pattern)
        count = matching_jobs.update(payroll_category=category)
        if count:
            print(f"  Set payroll_category for {count} jobs matching '{pattern}'")


def noop(apps, schema_editor):
    """Reverse operation - do nothing (data migration is one-way)."""


class Migration(migrations.Migration):

    dependencies = [
        ("workflow", "0185_fix_unpaid_leave_and_remove_posts_to_xero"),
        ("job", "0061_job_payroll_category"),
    ]

    operations = [
        # Step 1: Add xero_name field (temporarily allow null)
        migrations.AddField(
            model_name="payrollcategory",
            name="xero_name",
            field=models.CharField(
                help_text="Xero name for lookup (Leave Type name or Earnings Rate name)",
                max_length=100,
                null=True,
            ),
        ),
        # Step 2: Migrate data to xero_name
        migrations.RunPython(migrate_xero_names_forward, noop),
        # Step 3: Set payroll_category FK on leave jobs
        migrations.RunPython(set_job_payroll_categories_forward, noop),
        # Step 4: Make xero_name non-null and unique
        migrations.AlterField(
            model_name="payrollcategory",
            name="xero_name",
            field=models.CharField(
                help_text="Xero name for lookup (Leave Type name or Earnings Rate name)",
                max_length=100,
                unique=True,
            ),
        ),
        # Step 5: Remove old fields
        migrations.RemoveField(
            model_name="payrollcategory",
            name="name",
        ),
        migrations.RemoveField(
            model_name="payrollcategory",
            name="display_name",
        ),
        migrations.RemoveField(
            model_name="payrollcategory",
            name="job_name_pattern",
        ),
        migrations.RemoveField(
            model_name="payrollcategory",
            name="xero_leave_type_name",
        ),
        migrations.RemoveField(
            model_name="payrollcategory",
            name="xero_earnings_rate_name",
        ),
        # Step 6: Update Meta ordering and help texts
        migrations.AlterModelOptions(
            name="payrollcategory",
            options={
                "ordering": ["xero_name"],
                "verbose_name": "Payroll Category",
                "verbose_name_plural": "Payroll Categories",
            },
        ),
        migrations.AlterField(
            model_name="payrollcategory",
            name="rate_multiplier",
            field=models.DecimalField(
                blank=True,
                decimal_places=1,
                help_text="Rate multiplier for work entries (e.g., 1.0, 1.5, 2.0). NULL for leave categories.",
                max_digits=3,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="payrollcategory",
            name="uses_leave_api",
            field=models.BooleanField(
                default=False,
                help_text="True = use Xero Leave API. False = use Xero Timesheets API.",
            ),
        ),
    ]
