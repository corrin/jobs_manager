# Generated by Django 5.0.6 on 2024-09-15 09:01

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("workflow", "0002_remove_adjustmententry_job_pricing_type_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="jobpricing",
            name="id",
            field=models.UUIDField(
                default=uuid.uuid4, editable=False, primary_key=True, serialize=False
            ),
        ),
    ]
