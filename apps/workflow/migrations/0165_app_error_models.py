import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("workflow", "0164_serviceapikey"),
    ]

    operations = [
        migrations.CreateModel(
            name="AppError",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        primary_key=True, default=uuid.uuid4, editable=False
                    ),
                ),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
                ("message", models.TextField()),
                ("data", models.JSONField(blank=True, null=True)),
            ],
            options={
                "db_table": "workflow_app_error",
                "ordering": ["-timestamp"],
            },
        ),
        migrations.CreateModel(
            name="XeroError",
            fields=[
                (
                    "apperror_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=models.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="workflow.apperror",
                    ),
                ),
                ("entity", models.CharField(max_length=100)),
                ("reference_id", models.CharField(max_length=255)),
                ("kind", models.CharField(max_length=50)),
            ],
            options={
                "db_table": "workflow_xero_error",
            },
            bases=("workflow.apperror",),
        ),
    ]
