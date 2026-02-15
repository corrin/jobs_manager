"""Service for auto-archiving recently completed jobs that are paid."""

import logging
from dataclasses import dataclass, field
from datetime import timedelta
from typing import List

from django.db import transaction
from django.utils import timezone

from apps.job.models import Job, JobEvent

logger = logging.getLogger(__name__)


@dataclass
class AutoArchiveResult:
    """Result of auto-archive operation."""

    jobs_archived: int
    duration_seconds: float
    archived_jobs: List[Job] = field(default_factory=list)


class AutoArchiveService:
    """Service for auto-archiving recently completed, paid jobs."""

    @staticmethod
    def auto_archive_completed_jobs(
        dry_run: bool = False, verbose: bool = False
    ) -> AutoArchiveResult:
        """
        Archive recently_completed jobs that are paid and have been
        in that status for 6+ days.

        Args:
            dry_run: If True, don't make any changes
            verbose: If True, log detailed information

        Returns:
            AutoArchiveResult with operation details
        """
        start_time = timezone.now()
        threshold = timezone.now() - timedelta(days=6)

        eligible_jobs = Job.objects.filter(
            status="recently_completed",
            paid=True,
            completed_at__lte=threshold,
        )

        if verbose:
            logger.info(
                f"Found {eligible_jobs.count()} recently completed, paid jobs "
                f"older than 6 days"
            )

        archived_jobs = []

        for job in eligible_jobs:
            if verbose:
                logger.info(
                    f"Job {job.job_number} - {job.name}: "
                    f"completed_at={job.completed_at}, paid={job.paid}"
                )
            if dry_run:
                logger.info(f"Would archive job {job.job_number} - {job.name}")
            archived_jobs.append(job)

        if not dry_run and archived_jobs:
            with transaction.atomic():
                for job in archived_jobs:
                    job.status = "archived"
                    job.save(update_fields=["status"])

                    JobEvent.objects.create(
                        job=job,
                        event_type="status_changed",
                        description=(
                            "Auto-archived: job was recently completed, paid, "
                            "and 6+ days old."
                        ),
                        staff=None,
                    )

                    logger.info(f"Job {job.job_number} ({job.name}) auto-archived")

        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()

        return AutoArchiveResult(
            jobs_archived=len(archived_jobs),
            duration_seconds=duration,
            archived_jobs=archived_jobs,
        )
