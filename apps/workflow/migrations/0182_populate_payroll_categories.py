# Generated manually for data migration
from decimal import Decimal

from django.db import migrations


def populate_payroll_categories(apps, schema_editor):
    """
    Create initial PayrollCategory records and copy Xero IDs from CompanyDefaults.
    """
    PayrollCategory = apps.get_model("workflow", "PayrollCategory")
    apps.get_model("workflow", "CompanyDefaults")

    # Don't query CompanyDefaults - the xero_*_earnings_rate_name fields
    # may not exist in schema and are removed by migration 0183 anyway.
    defaults = None

    # Define the initial categories
    categories = [
        # Leave types - matched by job name pattern
        {
            "name": "annual_leave",
            "display_name": "Annual Leave",
            "job_name_pattern": "annual leave",
            "rate_multiplier": None,
            "posts_to_xero": True,
            "uses_leave_api": True,
            "xero_leave_type_name": "Annual Leave",
            "xero_earnings_rate_name": None,
        },
        {
            "name": "sick_leave",
            "display_name": "Sick Leave",
            "job_name_pattern": "sick leave",
            "rate_multiplier": None,
            "posts_to_xero": True,
            "uses_leave_api": True,
            "xero_leave_type_name": "Sick Leave",
            "xero_earnings_rate_name": None,
        },
        {
            "name": "other_leave",
            "display_name": "Other Leave",
            "job_name_pattern": "other leave",
            "rate_multiplier": None,
            "posts_to_xero": True,
            "uses_leave_api": False,
            "xero_leave_type_name": None,
            "xero_earnings_rate_name": None,
        },
        {
            "name": "unpaid_leave",
            "display_name": "Unpaid Leave",
            "job_name_pattern": "unpaid leave",
            "rate_multiplier": None,
            "posts_to_xero": False,
            "uses_leave_api": False,
            "xero_leave_type_name": "Unpaid Leave",
            "xero_earnings_rate_name": None,
        },
        # Work types - matched by rate multiplier
        {
            "name": "work_ordinary",
            "display_name": "Ordinary Time",
            "job_name_pattern": None,
            "rate_multiplier": Decimal("1.0"),
            "posts_to_xero": True,
            "uses_leave_api": False,
            "xero_leave_type_name": None,
            "xero_earnings_rate_name": (
                getattr(defaults, "xero_ordinary_earnings_rate_name", None)
                if defaults
                else None
            ),
        },
        {
            "name": "work_time_half",
            "display_name": "Time and a Half",
            "job_name_pattern": None,
            "rate_multiplier": Decimal("1.5"),
            "posts_to_xero": True,
            "uses_leave_api": False,
            "xero_leave_type_name": None,
            "xero_earnings_rate_name": (
                getattr(defaults, "xero_time_half_earnings_rate_name", None)
                if defaults
                else None
            ),
        },
        {
            "name": "work_double",
            "display_name": "Double Time",
            "job_name_pattern": None,
            "rate_multiplier": Decimal("2.0"),
            "posts_to_xero": True,
            "uses_leave_api": False,
            "xero_leave_type_name": None,
            "xero_earnings_rate_name": (
                getattr(defaults, "xero_double_time_earnings_rate_name", None)
                if defaults
                else None
            ),
        },
    ]

    for cat_data in categories:
        PayrollCategory.objects.create(**cat_data)


def reverse_populate(apps, schema_editor):
    """
    Remove all PayrollCategory records.
    """
    PayrollCategory = apps.get_model("workflow", "PayrollCategory")
    PayrollCategory.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("workflow", "0181_payrollcategory"),
    ]

    operations = [
        migrations.RunPython(populate_payroll_categories, reverse_populate),
    ]
