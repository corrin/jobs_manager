"""Backfill completed_at for jobs in recently_completed or archived status.

Strategy:
1. Use the earliest status_changed event that moved the job to
   'Recently Completed' or 'Archived' (most accurate).
2. Fall back to the latest accounting_date from actual CostLines
   (for older jobs predating the event system).
3. Fall back to updated_at (for archived jobs with no cost lines).
"""

import datetime

from django.db import migrations
from django.db.models import Max, Q


def backfill_completed_at(apps, schema_editor):
    Job = apps.get_model("job", "Job")
    JobEvent = apps.get_model("job", "JobEvent")
    CostLine = apps.get_model("job", "CostLine")

    completed_jobs = Job.objects.filter(
        status__in=("recently_completed", "archived"),
        completed_at__isnull=True,
    )

    for job in completed_jobs.iterator():
        # Strategy 1: earliest event moving job to a completed status
        event = (
            JobEvent.objects.filter(
                job=job,
                event_type="status_changed",
            )
            .filter(
                Q(description__contains="to 'Recently Completed'")
                | Q(description__contains="to 'Archived'")
            )
            .order_by("timestamp")
            .first()
        )

        if event:
            job.completed_at = event.timestamp
            job.save(update_fields=["completed_at"])
            continue

        # Strategy 2: latest accounting_date from actual CostLines
        # (same query as Job.last_financial_activity_date property)
        if job.latest_actual_id:
            latest_date = CostLine.objects.filter(
                cost_set_id=job.latest_actual_id,
            ).aggregate(latest=Max("accounting_date"))["latest"]

            if latest_date:
                job.completed_at = datetime.datetime.combine(
                    latest_date,
                    datetime.time.min,
                    tzinfo=datetime.timezone.utc,
                )
                job.save(update_fields=["completed_at"])
                continue

        # Strategy 3: updated_at as last resort
        job.completed_at = job.updated_at
        job.save(update_fields=["completed_at"])


def reverse_backfill(apps, schema_editor):
    Job = apps.get_model("job", "Job")
    Job.objects.filter(completed_at__isnull=False).update(completed_at=None)


class Migration(migrations.Migration):

    dependencies = [
        ("job", "0068_add_completed_at_to_job"),
    ]

    operations = [
        migrations.RunPython(backfill_completed_at, reverse_backfill),
    ]
