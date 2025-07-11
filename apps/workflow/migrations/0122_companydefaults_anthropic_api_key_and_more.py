# Generated by Django 5.1.5 on 2025-04-16 10:26

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        (
            "workflow",
            "0121_purchaseorderline_alloy_purchaseorderline_location_and_more",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="companydefaults",
            name="anthropic_api_key",
            field=models.CharField(
                blank=True,
                help_text="API key for Anthropic Claude LLM",
                max_length=255,
                null=True,
            ),
        ),
        migrations.CreateModel(
            name="PurchaseOrderSupplierQuote",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("filename", models.CharField(max_length=255)),
                ("file_path", models.CharField(max_length=500)),
                ("mime_type", models.CharField(blank=True, max_length=100)),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                (
                    "extracted_data",
                    models.JSONField(
                        blank=True, help_text="Extracted data from the quote", null=True
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[("active", "Active"), ("deleted", "Deleted")],
                        default="active",
                        max_length=20,
                    ),
                ),
                (
                    "purchase_order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="quotes",
                        to="workflow.purchaseorder",
                    ),
                ),
            ],
        ),
    ]
