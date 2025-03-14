# Generated by Django 5.0.6 on 2024-11-06 03:48

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("workflow", "0025_historicaljob_latest_estimate_pricing_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="job",
            name="latest_estimate_pricing",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="latest_estimate_for_job",
                to="workflow.jobpricing",
            ),
        ),
        migrations.AlterField(
            model_name="job",
            name="latest_quote_pricing",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="latest_quote_for_job",
                to="workflow.jobpricing",
            ),
        ),
        migrations.AlterField(
            model_name="job",
            name="latest_reality_pricing",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="latest_reality_for_job",
                to="workflow.jobpricing",
            ),
        ),
    ]
