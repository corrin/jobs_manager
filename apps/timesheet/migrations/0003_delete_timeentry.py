# Generated by Django 5.2 on 2025-07-07 20:36

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("timesheet", "0002_alter_timeentry_job_pricing_fk"),
        ("job", "0030_migrate_pricing_to_costing_and_cleanup"),
    ]

    operations = [
        migrations.DeleteModel(
            name="TimeEntry",
        ),
    ]
