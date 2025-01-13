# Generated by Django 5.1.4 on 2025-01-02 06:04

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("workflow", "0067_supplier_purchase_purchaseline_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="purchase",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True, default=django.utils.timezone.now
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="purchase",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name="purchaseorder",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True, default=django.utils.timezone.now
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="purchaseorder",
            name="job",
            field=models.ForeignKey(
                blank=True,
                help_text="Primary job this PO is for",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="workflow.job",
            ),
        ),
        migrations.AddField(
            model_name="purchaseorder",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name="purchaseline",
            name="purchase",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="lines",
                to="workflow.purchase",
            ),
        ),
    ]