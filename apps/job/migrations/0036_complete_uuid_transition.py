# Complete JobEvent UUID transition - Step 2

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("job", "0035_alter_jobevent_id"),
    ]

    operations = [
        # Step 3: Make temp_uuid_id non-nullable
        migrations.AlterField(
            model_name="jobevent",
            name="temp_uuid_id",
            field=models.UUIDField(default=uuid.uuid4, editable=False),
        ),
        # Step 4: Remove old integer id field
        migrations.RemoveField(
            model_name="jobevent",
            name="id",
        ),
    ]
