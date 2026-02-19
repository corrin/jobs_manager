"""Add completed_at to Job and backfill from historical data."""

import datetime

from django.db import migrations, models
from django.db.models import Max, Q


def backfill_completed_at(apps, schema_editor):
    """Backfill completed_at for jobs already in a completed status."""
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
            JobEvent.objects.filter(job=job, event_type="status_changed")
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
        if job.latest_actual_id:
            latest_date = CostLine.objects.filter(
                cost_set_id=job.latest_actual_id
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
    """No-op reverse: completed_at field will be dropped."""


class Migration(migrations.Migration):

    dependencies = [
        ("job", "0067_normalize_wage_rate_multiplier"),
    ]

    operations = [
        migrations.AddField(
            model_name="historicaljob",
            name="completed_at",
            field=models.DateTimeField(
                blank=True,
                help_text="Set automatically when job moves to recently_completed or archived",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="job",
            name="completed_at",
            field=models.DateTimeField(
                blank=True,
                help_text="Set automatically when job moves to recently_completed or archived",
                null=True,
            ),
        ),
        migrations.RunPython(backfill_completed_at, reverse_backfill),
    ]
