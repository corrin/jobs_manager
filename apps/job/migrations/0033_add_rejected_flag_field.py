# Migration to add rejected_flag field to Job model
# This field tracks jobs that were rejected and are now in recently_completed status

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("job", "0032_fix_blank_job_names"),
    ]

    operations = [
        migrations.AddField(
            model_name="job",
            name="rejected_flag",
            field=models.BooleanField(
                default=False,
                help_text="Indicates if this job was rejected (shown in Recently Completed with rejected styling)",
            ),
        ),
    ]
