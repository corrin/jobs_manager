"""Add base_wage_rate to Staff and populate from existing wage_rate."""

import logging
from decimal import Decimal

from django.db import migrations, models

logger = logging.getLogger(__name__)


def populate_base_wage_rate(apps, schema_editor):
    """Copy current wage_rate -> base_wage_rate for all staff."""
    Staff = apps.get_model("accounts", "Staff")
    count = 0
    for staff in Staff.objects.all():
        staff.base_wage_rate = staff.wage_rate
        staff.save(update_fields=["base_wage_rate"])
        count += 1
    print(f"  Populated base_wage_rate for {count} staff (copied from wage_rate)")


def reverse_populate(apps, schema_editor):
    """No-op reverse: base_wage_rate field will be dropped."""


def recompute_loaded_wage_rates(apps, schema_editor):
    """Set wage_rate = base_wage_rate * (1 + annual_leave_loading/100) for all staff."""
    Staff = apps.get_model("accounts", "Staff")
    staff_to_update = list(Staff.objects.filter(base_wage_rate__gt=0))
    if not staff_to_update:
        print("  No staff with base_wage_rate > 0, skipping recompute")
        return

    CompanyDefaults = apps.get_model("workflow", "CompanyDefaults")
    if not CompanyDefaults.objects.exists():
        # Restore path: CompanyDefaults loaded from fixture after migrations.
        print(
            f"  WARNING: {len(staff_to_update)} staff need wage_rate recompute but "
            f"CompanyDefaults does not exist yet (expected during restore). "
            f"wage_rate left equal to base_wage_rate. "
            f"Leave loading will be applied on next Staff save after fixture load."
        )
        logger.warning(
            "Skipped wage_rate recompute for %d staff — no CompanyDefaults row. "
            "If this is not a restore, something is wrong.",
            len(staff_to_update),
        )
        return

    defaults = CompanyDefaults.objects.get()
    loading = defaults.annual_leave_loading
    multiplier = Decimal("1") + loading / Decimal("100")
    print(
        f"  Recomputing wage_rate for {len(staff_to_update)} staff "
        f"(leave loading {loading}%, multiplier {multiplier})"
    )

    for staff in staff_to_update:
        staff.wage_rate = (staff.base_wage_rate * multiplier).quantize(Decimal("0.01"))
        staff.save(update_fields=["wage_rate"])
    print(f"  Done — {len(staff_to_update)} staff wage_rates updated")


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
        migrations.AddField(
            model_name="historicalstaff",
            name="base_wage_rate",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Actual hourly pay rate. wage_rate is auto-computed with leave loading.",
                max_digits=10,
            ),
        ),
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
        migrations.RunPython(populate_base_wage_rate, reverse_populate),
        migrations.RunPython(recompute_loaded_wage_rates, reverse_recompute),
    ]
