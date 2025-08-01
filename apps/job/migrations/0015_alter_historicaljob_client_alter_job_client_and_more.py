# Generated by Django 5.2 on 2025-06-05 19:36

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("client", "0001_initial"),
        ("job", "0014_alter_jobpart_table"),
        ("purchasing", "0007_stock_unique_xero_id"),
    ]

    operations = [
        migrations.AlterField(
            model_name="historicaljob",
            name="client",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="client.client",
            ),
        ),
        migrations.AlterField(
            model_name="job",
            name="client",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="jobs",
                to="client.client",
            ),
        ),
        migrations.AlterField(
            model_name="materialentry",
            name="source_stock",
            field=models.ForeignKey(
                blank=True,
                help_text="The Stock item consumed to create this entry",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="consumed_entries",
                to="purchasing.stock",
            ),
        ),
    ]
