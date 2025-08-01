# Generated by Django 5.2 on 2025-06-02 20:01

import uuid

import django.db.models.deletion
from django.db import migrations, models


# !!!!!
# This migration is meant to be faked in existing dbs. Its only purpose is to create the tables when creating a fresh db.
class Migration(migrations.Migration):
    dependencies = [
        ("job", "0005_remove_materialentry_source_stock_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="JobPart",
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
                ("name", models.CharField(max_length=100)),
                ("description", models.TextField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "job_pricing",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="parts",
                        to="job.jobpricing",
                    ),
                ),
            ],
            options={
                "db_table": "workflow_jobpart",
                "ordering": ["created_at"],
            },
        ),
    ]
