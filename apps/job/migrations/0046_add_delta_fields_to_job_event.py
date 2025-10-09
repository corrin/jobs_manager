from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("job", "0045_create_job_delta_rejection"),
    ]

    operations = [
        migrations.AddField(
            model_name="jobevent",
            name="schema_version",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="jobevent",
            name="change_id",
            field=models.UUIDField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="jobevent",
            name="delta_before",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="jobevent",
            name="delta_after",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="jobevent",
            name="delta_meta",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="jobevent",
            name="delta_checksum",
            field=models.CharField(blank=True, default="", max_length=128),
        ),
        migrations.AddIndex(
            model_name="jobevent",
            index=models.Index(fields=["change_id"], name="jobevent_change_idx"),
        ),
    ]
