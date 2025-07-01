# Migration to update existing job statuses for new kanban categorization
# This migration maps old statuses to new ones where needed

from django.db import migrations


def update_job_statuses(apps, schema_editor):
    """
    Update job statuses for new kanban categorization:
    1. Maps 'approved' to 'accepted_quote' for consistency
    2. Maps 'completed' to 'recently_completed' for new workflow
    """
    Job = apps.get_model("job", "Job")

    # Map old statuses to new ones
    status_mapping = {
        "approved": "accepted_quote",  # Update approved to accepted_quote
        "completed": "recently_completed",  # Jobs that were completed become recently_completed
    }

    for old_status, new_status in status_mapping.items():
        updated_count = Job.objects.filter(status=old_status).update(status=new_status)
        if updated_count > 0:
            print(f"Updated {updated_count} jobs from '{old_status}' to '{new_status}'")


def reverse_job_statuses(apps, schema_editor):
    """
    Reverse the status updates if needed
    """
    Job = apps.get_model("job", "Job")

    # Reverse mapping
    reverse_mapping = {
        "accepted_quote": "approved",
        "recently_completed": "completed",
    }

    for new_status, old_status in reverse_mapping.items():
        # Only reverse if the old status existed
        updated_count = Job.objects.filter(status=new_status).update(status=old_status)
        if updated_count > 0:
            print(
                f"Reverted {updated_count} jobs from '{new_status}' to '{old_status}'"
            )


class Migration(migrations.Migration):
    dependencies = [
        ("job", "0024_rename_pricing_jobpricing"),
    ]

    operations = [
        migrations.RunPython(update_job_statuses, reverse_job_statuses, elidable=True),
    ]
