# Generated by Django 5.0.6 on 2024-12-06 19:31

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("workflow", "0060_xerojournal_xerojournallineitem"),
    ]

    operations = [
        migrations.AddField(
            model_name="xerojournallineitem",
            name="xero_last_modified",
            field=models.DateTimeField(default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]
