import datetime
import uuid
from typing import Dict, List

from django.db import models, transaction
from django.utils import timezone
from simple_history.models import HistoricalRecords  # type: ignore


class Job(models.Model):
    name = models.CharField(max_length=100)  # type: ignore

    id: uuid.UUID = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )  # type: ignore

    JOB_STATUS_CHOICES: List[tuple[str, str]] = [
        ("quoting", "Quoting"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("in_progress", "In Progress"),
        ("on_hold", "On Hold"),
        ("special", "Special"),
        ("completed", "Completed"),
        ("archived", "Archived"),
    ]

    STATUS_TOOLTIPS: Dict[str, str] = {
        "quoting": "The quote is currently being prepared.",
        "approved": "The quote has been approved, but work hasn't started yet.",
        "rejected": "The quote was declined.",
        "in_progress": "Work has started on this job.",
        "on_hold": "The job is on hold, possibly awaiting materials.",
        "special": "Shop jobs, upcoming shutdowns, etc.",
        "completed": "Work has finished on this job.",
        "archived": "The job has been paid for and picked up.",
    }

    job_name: str = models.CharField(max_length=100, null=False, blank=False)  # type: ignore
    client_name: str = models.CharField(max_length=100)  # type: ignore
    order_number: str = models.CharField(
        max_length=100, null=True, blank=True
    )  # type: ignore
    contact_person: str = models.CharField(max_length=100)  # type: ignore
    contact_phone: str = models.CharField(max_length=15)  # type: ignore
    job_number = models.IntegerField(unique=True, null=False, blank=False)
    description: str = models.TextField()  # type: ignore
    date_created: datetime.datetime = models.DateTimeField(
        default=timezone.now
    )  # type: ignore
    last_updated: datetime.datetime = models.DateTimeField(
        auto_now=True
    )  # type: ignore
    status: str = models.CharField(
        max_length=30, choices=JOB_STATUS_CHOICES, default="quoting"
    )  # type: ignore
    # Decided not to bother with parent for now since we don't have a hierarchy of jobs.
    # Can be restored.  Would also provide an alternative to historical records for tracking changes.
    # parent: models.ForeignKey = models.ForeignKey(
    #     "self",
    #     null=True,
    #     blank=True,
    #     related_name="revisions",
    #     on_delete=models.SET_NULL,
    # )
    paid: bool = models.BooleanField(default=False)  # type: ignore
    history: HistoricalRecords = HistoricalRecords()

    def save(self, *args, **kwargs):
        if not self.job_number:
            with transaction.atomic():
                # Select the last job for update and increment the job number
                last_job = Job.objects.select_for_update().order_by("id").last()
                if last_job:
                    self.job_number = last_job.job_number + 1
                else:
                    self.job_number = 1  # Start from 1 if no jobs exist
        super(Job, self).save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.client_name} - {self.job_number or self.order_number}"

    def get_display_name(self) -> str:
        return f"Job:{self.job_number}"  # type: ignore