from django.db import models
from django.utils.timezone import now

from apps.accounts.models import Staff


class JobEvent(models.Model):
    job = models.ForeignKey(
        "Job", on_delete=models.CASCADE, related_name="events", null=True, blank=True
    )
    timestamp = models.DateTimeField(default=now)
    staff = models.ForeignKey(Staff, on_delete=models.SET_NULL, null=True, blank=True)
    event_type = models.CharField(
        max_length=100, null=False, blank=False, default="automatic_event"
    )  # e.g., "status_change", "manual_note"
    description = models.TextField()

    def __str__(self) -> str:
        return f"{self.timestamp}: {self.event_type} for {self.job.name}"

    class Meta:
        db_table = "workflow_jobevent"
        ordering = ["-timestamp"]
