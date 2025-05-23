# Generated by Django 5.1.5 on 2025-04-03 08:55

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("workflow", "0117_alter_stock_metal_type"),
    ]

    operations = [
        # Clear existing references to avoid conversion errors
        migrations.RunSQL(
            "UPDATE workflow_materialentry SET source_stock_id = NULL WHERE source_stock_id IS NOT NULL;"
        ),
        
        # Let Django handle the column type change
        migrations.AlterField(
            model_name="materialentry",
            name="source_stock",
            field=models.ForeignKey(
                blank=True,
                help_text="The Stock item consumed to create this entry",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="consumed_entries",
                to="workflow.stock",
            ),
        ),
    ]