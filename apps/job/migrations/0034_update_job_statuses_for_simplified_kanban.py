# Migration to update job statuses for simplified kanban columns
# Maps existing statuses to new 6-column kanban structure

import logging

from django.db import migrations

logger = logging.getLogger(__name__)


def update_job_statuses_for_simplified_kanban(apps, schema_editor):
    """
    Update job statuses for simplified kanban with 6 columns based on Corrin's mapping:
    - Draft: draft (maps from quoting)
    - Awaiting Approval: awaiting_approval (start empty, manual moves expected)
    - Approved: approved (maps from accepted_quote)
    - In Progress: in_progress (unchanged)
    - Unusual: unusual (maps from awaiting_materials, awaiting_staff, awaiting_site_availability, on_hold)
    - Recently Completed: recently_completed (maps from completed, rejected with rejected_flag=True)

    Hidden statuses: special (not visible without advanced search), archived (unchanged)
    """
    Job = apps.get_model("job", "Job")

    # Map old statuses to new ones based on Corrin's table
    status_mapping = {
        # Quoting -> Draft (not awaiting_approval as previously thought)
        "quoting": "draft",
        # Accepted Quote -> Approved
        "accepted_quote": "approved",
        # All waiting states -> Unusual (not in_progress)
        "awaiting_materials": "unusual",
        "awaiting_staff": "unusual",
        "awaiting_site_availability": "unusual",
        # On Hold -> Unusual
        "on_hold": "unusual",
        # Completed -> Recently Completed
        "completed": "recently_completed",
    }

    total_updated = 0
    for old_status, new_status in status_mapping.items():
        updated_count = Job.objects.filter(status=old_status).update(status=new_status)
        if updated_count > 0:
            logger.info(
                f"Updated {updated_count} jobs from '{old_status}' to '{new_status}'"
            )
            total_updated += updated_count

    # Special handling for rejected jobs - set rejected_flag=True and status=recently_completed
    rejected_jobs = Job.objects.filter(status="rejected")
    rejected_count = rejected_jobs.update(
        status="recently_completed", rejected_flag=True
    )
    if rejected_count > 0:
        logger.info(
            f"Updated {rejected_count} rejected jobs to recently_completed with rejected_flag=True"
        )
        total_updated += rejected_count

    # Log statuses that remain unchanged
    unchanged_statuses = [
        "draft",
        "awaiting_approval",
        "approved",
        "in_progress",
        "unusual",
        "recently_completed",
        "special",
        "archived",
    ]
    for status in unchanged_statuses:
        count = Job.objects.filter(status=status).count()
        if count > 0:
            logger.info(f"Left {count} jobs with status '{status}' unchanged")

    logger.info(f"Total jobs updated: {total_updated}")


def reverse_job_statuses_for_simplified_kanban(apps, schema_editor):
    """
    Reverse the status updates if migration needs to be rolled back
    """
    Job = apps.get_model("job", "Job")

    # Reverse mapping - note that some mappings are lossy
    # Multiple old statuses mapped to single new ones, so we map back to most common
    reverse_mapping = {
        "draft": "quoting",  # Draft came from quoting
        "approved": "accepted_quote",  # Approved came from accepted_quote
        "unusual": "awaiting_materials",  # Default unusual back to awaiting_materials
        "recently_completed": "completed",  # Default back to completed (rejected will be lost)
        # awaiting_approval and in_progress stay unchanged
    }

    total_reverted = 0
    for new_status, old_status in reverse_mapping.items():
        updated_count = Job.objects.filter(status=new_status).update(status=old_status)
        if updated_count > 0:
            logger.info(
                f"Reverted {updated_count} jobs from '{new_status}' to '{old_status}'"
            )
            total_reverted += updated_count

    logger.info(f"Total jobs reverted: {total_reverted}")


class Migration(migrations.Migration):
    dependencies = [
        ("job", "0033_add_rejected_flag_field"),
    ]

    operations = [
        migrations.RunPython(
            update_job_statuses_for_simplified_kanban,
            reverse_job_statuses_for_simplified_kanban,
        ),
    ]
