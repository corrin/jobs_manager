# Generated by Django 5.2 on 2025-06-04 13:54

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("workflow", "0153_delete_client_client"),
        ("purchasing", "0002_move_purchase_models_database"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(name="PurchaseOrder"),
                migrations.DeleteModel(name="PurchaseOrderLine"),
                migrations.DeleteModel(name="PurchaseOrderSupplierQuote"),
                migrations.CreateModel(
                    name="PurchaseOrder",
                    fields=[],
                    options={
                        "proxy": True,
                        "indexes": [],
                        "constraints": [],
                    },
                    bases=("purchasing.purchaseorder",),
                ),
                migrations.CreateModel(
                    name="PurchaseOrderLine",
                    fields=[],
                    options={
                        "proxy": True,
                        "indexes": [],
                        "constraints": [],
                    },
                    bases=("purchasing.purchaseorderline",),
                ),
                migrations.CreateModel(
                    name="PurchaseOrderSupplierQuote",
                    fields=[],
                    options={
                        "proxy": True,
                        "indexes": [],
                        "constraints": [],
                    },
                    bases=("purchasing.purchaseordersupplierquote",),
                ),
                migrations.RemoveField(
                    model_name="stock",
                    name="source_purchase_order_line",
                ),
                migrations.AddField(
                    model_name="stock",
                    name="source_purchase_order_line",
                    field=models.ForeignKey(
                        blank=True,
                        help_text="The PO line this stock originated from (if source='purchase_order')",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="stock_generated",
                        to="purchasing.purchaseorderline",
                    ),
                ),
            ],
            database_operations=[],
        ),
    ]
