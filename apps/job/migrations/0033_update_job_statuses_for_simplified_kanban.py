# Migration to update job statuses for simplified kanban columns
# Maps existing statuses to new 6-column kanban structure

import logging

from django.db import migrations, models

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
        ("job", "0032_fix_blank_job_names"),
    ]

    operations = [
        # Add the rejected_flag field to both Job and HistoricalJob models
        migrations.AddField(
            model_name="job",
            name="rejected_flag",
            field=models.BooleanField(
                default=False,
                help_text="Indicates if this job was rejected (shown in Recently Completed with rejected styling)",
            ),
        ),
        migrations.AddField(
            model_name="historicaljob",
            name="rejected_flag",
            field=models.BooleanField(
                default=False,
                help_text="Indicates if this job was rejected (shown in Recently Completed with rejected styling)",
            ),
        ),
        # Update status choices for both models
        migrations.AlterField(
            model_name="job",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("awaiting_approval", "Awaiting Approval"),
                    ("approved", "Approved"),
                    ("in_progress", "In Progress"),
                    ("unusual", "Unusual"),
                    ("recently_completed", "Recently Completed"),
                    ("special", "Special"),
                    ("archived", "Archived"),
                    ("quoting", "Quoting"),
                    ("accepted_quote", "Accepted Quote"),
                    ("awaiting_materials", "Awaiting Materials"),
                    ("awaiting_staff", "Awaiting Staff"),
                    ("awaiting_site_availability", "Awaiting Site Availability"),
                    ("on_hold", "On Hold"),
                    ("completed", "Completed"),
                    ("rejected", "Rejected"),
                ],
                default="draft",
                max_length=30,
            ),
        ),
        migrations.AlterField(
            model_name="historicaljob",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("awaiting_approval", "Awaiting Approval"),
                    ("approved", "Approved"),
                    ("in_progress", "In Progress"),
                    ("unusual", "Unusual"),
                    ("recently_completed", "Recently Completed"),
                    ("special", "Special"),
                    ("archived", "Archived"),
                    ("quoting", "Quoting"),
                    ("accepted_quote", "Accepted Quote"),
                    ("awaiting_materials", "Awaiting Materials"),
                    ("awaiting_staff", "Awaiting Staff"),
                    ("awaiting_site_availability", "Awaiting Site Availability"),
                    ("on_hold", "On Hold"),
                    ("completed", "Completed"),
                    ("rejected", "Rejected"),
                ],
                default="draft",
                max_length=30,
            ),
        ),
        # Update pricing methodology choices for both models
        migrations.AlterField(
            model_name="job",
            name="pricing_methodology",
            field=models.CharField(
                choices=[
                    ("time_materials", "Time & Materials"),
                    ("fixed_price", "Fixed Price"),
                ],
                default="time_materials",
                help_text="Determines whether job uses quotes or time and materials pricing type.",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="historicaljob",
            name="pricing_methodology",
            field=models.CharField(
                choices=[
                    ("time_materials", "Time & Materials"),
                    ("fixed_price", "Fixed Price"),
                ],
                default="time_materials",
                help_text="Determines whether job uses quotes or time and materials pricing type.",
                max_length=20,
            ),
        ),
        # Finally, update the job statuses using the new field
        migrations.RunPython(
            update_job_statuses_for_simplified_kanban,
            reverse_job_statuses_for_simplified_kanban,
        ),
    ]
