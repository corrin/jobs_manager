# Generated by Django 5.0.6 on 2024-12-06 19:38

import datetime

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("workflow", "0061_xerojournallineitem_xero_last_modified"),
    ]

    operations = [
        migrations.AddField(
            model_name="xerojournal",
            name="xero_last_modified",
            field=models.DateTimeField(default=datetime.datetime.now),
            preserve_default=False,
        ),
    ]
