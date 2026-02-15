"""Rename KPI fields to kpi_* naming convention, add new fields.

Renames existing prod fields (preserving data), removes daily_gp_target
(replaced by kpi_daily_gp_green/amber), and adds annual_leave_loading,
financial_year_start_month, and XeroToken scope update.

Also zeros out Annual Leave XeroPayItem multipliers (was in deleted 0191).
"""

from decimal import Decimal

from django.db import migrations, models


def zero_annual_leave_pay_items(apps, schema_editor):
    """Set multiplier=0.0 on XeroPayItem entries containing 'Annual Leave'."""
    XeroPayItem = apps.get_model("workflow", "XeroPayItem")
    updated = XeroPayItem.objects.filter(
        name__icontains="annual leave",
        uses_leave_api=True,
    ).update(multiplier=Decimal("0.00"))
    if updated:
        print(f"  Updated {updated} Annual Leave XeroPayItem(s) to multiplier=0.0")


def reverse_zero_annual_leave(apps, schema_editor):
    """Restore Annual Leave multiplier to 1.0."""
    XeroPayItem = apps.get_model("workflow", "XeroPayItem")
    XeroPayItem.objects.filter(
        name__icontains="annual leave",
        uses_leave_api=True,
    ).update(multiplier=Decimal("1.00"))


def copy_gp_target_to_green(apps, schema_editor):
    """Copy daily_gp_target value into kpi_daily_gp_green before dropping it."""
    CompanyDefaults = apps.get_model("workflow", "CompanyDefaults")
    for cd in CompanyDefaults.objects.all():
        cd.kpi_daily_gp_green = cd.daily_gp_target
        cd.save(update_fields=["kpi_daily_gp_green"])


def reverse_copy_gp_target(apps, schema_editor):
    """No-op: daily_gp_target will be re-added by reverse migration."""


class Migration(migrations.Migration):

    dependencies = [
        ("workflow", "0190_add_openai_provider_type"),
    ]

    operations = [
        # --- Rename existing KPI fields to kpi_* convention ---
        migrations.RenameField(
            model_name="companydefaults",
            old_name="billable_threshold_amber",
            new_name="kpi_daily_billable_hours_amber",
        ),
        migrations.RenameField(
            model_name="companydefaults",
            old_name="billable_threshold_green",
            new_name="kpi_daily_billable_hours_green",
        ),
        migrations.RenameField(
            model_name="companydefaults",
            old_name="shop_hours_target_percentage",
            new_name="kpi_daily_shop_hours_percentage",
        ),
        # --- Add new KPI GP threshold fields ---
        migrations.AddField(
            model_name="companydefaults",
            name="kpi_daily_gp_green",
            field=models.DecimalField(
                decimal_places=2,
                default=1500.0,
                help_text="Daily gross profit above this threshold is marked in green",
                max_digits=10,
                verbose_name="Green Threshold of Daily GP",
            ),
        ),
        migrations.AddField(
            model_name="companydefaults",
            name="kpi_daily_gp_amber",
            field=models.DecimalField(
                decimal_places=2,
                default=0.0,
                help_text="Daily gross profit between this threshold and the green threshold is marked in amber",
                max_digits=10,
                verbose_name="Amber Threshold of Daily GP",
            ),
        ),
        # --- Copy daily_gp_target into kpi_daily_gp_green, then drop it ---
        migrations.RunPython(copy_gp_target_to_green, reverse_copy_gp_target),
        migrations.RemoveField(
            model_name="companydefaults",
            name="daily_gp_target",
        ),
        migrations.AddField(
            model_name="companydefaults",
            name="kpi_job_gp_target_percentage",
            field=models.DecimalField(
                decimal_places=2,
                default=50.0,
                help_text="Target gross profit margin percentage for jobs (used for color coding).  Set by looking at a year's history",
                max_digits=5,
                verbose_name="Job GP Target Percentage",
            ),
        ),
        # --- Add other new fields ---
        migrations.AddField(
            model_name="companydefaults",
            name="annual_leave_loading",
            field=models.DecimalField(
                decimal_places=2,
                default=8.00,
                help_text="Percentage added to base_wage_rate to get costing wage_rate (8.00 = 8%)",
                max_digits=5,
            ),
        ),
        migrations.RunPython(zero_annual_leave_pay_items, reverse_zero_annual_leave),
        migrations.AddField(
            model_name="companydefaults",
            name="financial_year_start_month",
            field=models.IntegerField(
                default=4,
                help_text="Month the financial year starts (1=January, 4=April, 7=July, etc.)",
            ),
        ),
        # --- Update XeroToken scope ---
        migrations.AlterField(
            model_name="xerotoken",
            name="scope",
            field=models.TextField(
                default="offline_access openid profile email accounting.contacts accounting.transactions accounting.attachments accounting.reports.read accounting.settings accounting.journals.read projects payroll.timesheets payroll.payruns payroll.payslip payroll.employees payroll.settings"
            ),
        ),
    ]
