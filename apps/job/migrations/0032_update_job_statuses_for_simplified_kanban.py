# Migration to update job statuses for simplified kanban columns
# Maps existing statuses to new 6-column kanban structure

import logging

from django.db import migrations

logger = logging.getLogger(__name__)


def update_job_statuses_for_simplified_kanban(apps, schema_editor):
    """
    Update job statuses for simplified kanban with 6 columns:
    - Draft: draft (unchanged)
    - Awaiting Approval: awaiting_approval (new, maps from quoting)
    - Approved: approved (maps from accepted_quote)
    - In Progress: in_progress (maps from awaiting_materials, awaiting_staff, awaiting_site_availability)
    - Unusual: unusual (maps from on_hold, special)
    - Recently Completed: recently_completed (maps from completed)

    Legacy statuses (rejected, archived) remain unchanged but hidden from kanban.
    """
    Job = apps.get_model("job", "Job")

    # Map old statuses to new ones
    status_mapping = {
        # Map quoting to awaiting_approval (quote submitted, waiting for customer approval)
        "quoting": "awaiting_approval",
        # Map accepted_quote back to approved (quote approved, ready to start)
        "accepted_quote": "approved",
        # Map various waiting states to in_progress (work has started or is ready to start)
        "awaiting_materials": "in_progress",
        "awaiting_staff": "in_progress",
        "awaiting_site_availability": "in_progress",
        # Map problematic statuses to unusual (requiring special attention)
        "on_hold": "unusual",
        "special": "unusual",
        # Map completed to recently_completed (just finished)
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

    # Log statuses that remain unchanged
    unchanged_statuses = ["draft", "rejected", "archived"]
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
        "awaiting_approval": "quoting",
        "approved": "accepted_quote",
        "in_progress": "awaiting_materials",  # Default back to awaiting_materials
        "unusual": "on_hold",  # Default back to on_hold
        "recently_completed": "completed",
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
        ("job", "0031_remove_jobpart_job_pricing_and_more"),
    ]

    operations = [
        migrations.RunPython(
            update_job_statuses_for_simplified_kanban,
            reverse_job_statuses_for_simplified_kanban,
        ),
    ]
