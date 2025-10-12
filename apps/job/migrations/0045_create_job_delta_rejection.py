import uuid

import django.db.models.deletion
from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):
    dependencies = [
        ("job", "0044_alter_costline_options_costline_created_at_and_more"),
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="JobDeltaRejection",
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
                ("change_id", models.UUIDField(blank=True, null=True)),
                ("reason", models.CharField(max_length=255)),
                ("detail", models.TextField(blank=True)),
                ("envelope", models.JSONField()),
                ("checksum", models.CharField(blank=True, max_length=128)),
                ("request_etag", models.CharField(blank=True, max_length=128)),
                ("request_ip", models.GenericIPAddressField(blank=True, null=True)),
                (
                    "created_at",
                    models.DateTimeField(default=timezone.now, editable=False),
                ),
                (
                    "job",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="delta_rejections",
                        to="job.job",
                    ),
                ),
                (
                    "staff",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="delta_rejections",
                        to="accounts.staff",
                    ),
                ),
            ],
            options={
                "db_table": "job_jobdeltarejection",
                "ordering": ("-created_at",),
            },
        ),
        migrations.AddIndex(
            model_name="jobdeltarejection",
            index=models.Index(
                fields=["change_id", "-created_at"],
                name="job_delta_rejection_change_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="jobdeltarejection",
            index=models.Index(
                fields=["-created_at"], name="job_delta_rejection_created_idx"
            ),
        ),
    ]
