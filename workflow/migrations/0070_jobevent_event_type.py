# Generated by Django 5.1.4 on 2025-01-11 16:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("workflow", "0069_rename_user_jobevent_staff"),
    ]

    operations = [
        migrations.AddField(
            model_name="jobevent",
            name="event_type",
            field=models.CharField(default="automatic_event", max_length=100),
        ),
    ]
