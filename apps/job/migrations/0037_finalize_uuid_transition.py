# Finalize JobEvent UUID transition - Step 3

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("job", "0036_complete_uuid_transition"),
    ]

    operations = [
        # Step 5: Rename temp_uuid_id to id and make it primary key
        migrations.RenameField(
            model_name="jobevent",
            old_name="temp_uuid_id",
            new_name="id",
        ),
        # Step 6: Make id the primary key
        migrations.AlterField(
            model_name="jobevent",
            name="id",
            field=models.UUIDField(
                primary_key=True, default=uuid.uuid4, editable=False, serialize=False
            ),
        ),
    ]
