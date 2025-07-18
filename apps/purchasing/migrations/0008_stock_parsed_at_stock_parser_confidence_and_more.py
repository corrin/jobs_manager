# Generated by Django 5.2 on 2025-06-16 09:04

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("purchasing", "0007_stock_unique_xero_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="stock",
            name="parsed_at",
            field=models.DateTimeField(
                blank=True,
                help_text="When this inventory item was parsed by LLM",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="stock",
            name="parser_confidence",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Parser confidence score 0.00-1.00",
                max_digits=3,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="stock",
            name="parser_version",
            field=models.CharField(
                blank=True,
                help_text="Version of parser used for this data",
                max_length=50,
                null=True,
            ),
        ),
    ]
