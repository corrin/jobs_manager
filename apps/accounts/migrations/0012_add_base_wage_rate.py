"""Add base_wage_rate to Staff and populate from existing wage_rate."""

from decimal import Decimal

from django.db import migrations, models


def populate_base_wage_rate(apps, schema_editor):
    """Copy current wage_rate → base_wage_rate for all staff."""
    Staff = apps.get_model("accounts", "Staff")
    for staff in Staff.objects.all():
        staff.base_wage_rate = staff.wage_rate
        staff.save(update_fields=["base_wage_rate"])


def reverse_populate(apps, schema_editor):
    """No-op reverse: base_wage_rate field will be dropped."""


def recompute_loaded_wage_rates(apps, schema_editor):
    """Set wage_rate = base_wage_rate * (1 + annual_leave_loading/100) for all staff."""
    CompanyDefaults = apps.get_model("workflow", "CompanyDefaults")
    Staff = apps.get_model("accounts", "Staff")

    try:
        defaults = CompanyDefaults.objects.get()
        loading = defaults.annual_leave_loading
    except CompanyDefaults.DoesNotExist:
        loading = Decimal("8.00")

    multiplier = Decimal("1") + loading / Decimal("100")
    for staff in Staff.objects.filter(base_wage_rate__gt=0):
        staff.wage_rate = (staff.base_wage_rate * multiplier).quantize(Decimal("0.01"))
        staff.save(update_fields=["wage_rate"])


def reverse_recompute(apps, schema_editor):
    """Reverse: restore wage_rate = base_wage_rate (remove loading)."""
    Staff = apps.get_model("accounts", "Staff")
    for staff in Staff.objects.filter(base_wage_rate__gt=0):
        staff.wage_rate = staff.base_wage_rate
        staff.save(update_fields=["wage_rate"])


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0011_remove_ims_payroll_fields"),
        ("workflow", "0191_add_annual_leave_loading"),
    ]

    operations = [
        # Step 1: Add the base_wage_rate field
        migrations.AddField(
            model_name="staff",
            name="base_wage_rate",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Actual hourly pay rate. wage_rate is auto-computed with leave loading.",
                max_digits=10,
            ),
        ),
        # Step 2: Copy wage_rate → base_wage_rate
        migrations.RunPython(populate_base_wage_rate, reverse_populate),
        # Step 3: Recompute wage_rate with leave loading applied
        migrations.RunPython(recompute_loaded_wage_rates, reverse_recompute),
    ]
