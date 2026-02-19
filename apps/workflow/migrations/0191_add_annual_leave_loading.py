"""Add annual_leave_loading to CompanyDefaults and zero out Annual Leave XeroPayItems."""

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


class Migration(migrations.Migration):

    dependencies = [
        ("workflow", "0190_add_openai_provider_type"),
    ]

    operations = [
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
    ]
