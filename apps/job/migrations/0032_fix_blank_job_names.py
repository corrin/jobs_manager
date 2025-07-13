# Generated migration to fix jobs with blank names
from django.db import migrations


def fix_blank_job_names(apps, schema_editor):
    """Fix jobs that have blank or null names which cause API validation errors."""
    Job = apps.get_model("job", "Job")

    # Find jobs with blank or null names
    blank_name_jobs = Job.objects.filter(name__isnull=True) | Job.objects.filter(
        name=""
    )
    count = blank_name_jobs.count()

    if count > 0:
        print(f"Fixing {count} jobs with blank names...")

        # Update each job to have a sensible default name
        for job in blank_name_jobs:
            job.name = f"Job #{job.job_number}"
            job.save()

        print(f"Fixed {count} jobs with blank names")
    else:
        print("No jobs with blank names found")


def reverse_fix_blank_job_names(apps, schema_editor):
    """Reverse migration - not implemented as we don't want to break names again."""
    print("Reverse migration not implemented - cannot safely restore blank names")


class Migration(migrations.Migration):
    dependencies = [
        ("job", "0031_remove_jobpart_job_pricing_and_more"),
    ]

    operations = [
        migrations.RunPython(fix_blank_job_names, reverse_fix_blank_job_names),
    ]
