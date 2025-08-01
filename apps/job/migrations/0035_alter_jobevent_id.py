# Generated by Django 5.2 on 2025-07-24 07:39

import uuid

from django.db import migrations, models


def populate_temp_uuid_ids(apps, schema_editor):
    """Generate UUIDs for existing JobEvent records"""
    JobEvent = apps.get_model("job", "JobEvent")
    for event in JobEvent.objects.all():
        event.temp_uuid_id = uuid.uuid4()
        event.save(update_fields=["temp_uuid_id"])


class Migration(migrations.Migration):
    dependencies = [
        ("job", "0034_remove_legacy_status_choices"),
    ]

    operations = [
        # Step 1: Add temporary UUID field
        migrations.AddField(
            model_name="jobevent",
            name="temp_uuid_id",
            field=models.UUIDField(default=uuid.uuid4, editable=False, null=True),
        ),
        # Step 2: Populate UUIDs for existing records
        migrations.RunPython(
            populate_temp_uuid_ids,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
