# Generated by Django 5.0.6 on 2024-11-06 04:06

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("workflow", "0026_alter_job_latest_estimate_pricing_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="jobpricing",
            name="job",
        ),
    ]