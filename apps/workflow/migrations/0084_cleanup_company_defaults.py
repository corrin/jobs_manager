from django.db import migrations


def cleanup_company_defaults(apps, schema_editor):
    """
    Ensure only one CompanyDefaults record exists.
    Keep the first record and delete any others.

    This migration handles two scenarios:
    1. Brand new empty database where we are applying all fixtures
    2. Existing database with a company defaults already
    """
    CompanyDefaults = apps.get_model("workflow", "CompanyDefaults")

    # Get all records
    records = list(CompanyDefaults.objects.all())

    if records:
        # Keep the first record
        keep_record = records[0]

        # Delete any other records
        CompanyDefaults.objects.exclude(pk=keep_record.pk).delete()
    else:
        # Check if we're in a fixture loading process
        # We'll skip creating a default record if we're in a fresh database setup
        # This allows fixtures to create the CompanyDefaults record instead
        pass


class Migration(migrations.Migration):
    dependencies = [
        ("workflow", "0083_setup_xero_sync_service"),
    ]

    operations = [
        # Run the cleanup function
        migrations.RunPython(
            cleanup_company_defaults, reverse_code=migrations.RunPython.noop
        ),
    ]
