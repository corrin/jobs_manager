# Generated by Django 5.0.6 on 2024-11-19 21:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("workflow", "0038_historicaljob_shop_job_job_shop_job"),
    ]

    operations = [
        migrations.AddField(
            model_name="historicaljob",
            name="charge_out_rate",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=10, null=True
            ),
        ),
        migrations.AddField(
            model_name="job",
            name="charge_out_rate",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=10, null=True
            ),
        ),
    ]