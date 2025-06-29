import uuid

from django.db import models


class AppError(models.Model):
    """Persistent record of an application error."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    message = models.TextField()
    data = models.JSONField(blank=True, null=True)

    class Meta:
        db_table = "workflow_app_error"
        ordering = ["-timestamp"]
        verbose_name = "Application Error"
        verbose_name_plural = "Application Errors"


class XeroError(AppError):
    """Specialised error raised during Xero synchronisation."""

    entity = models.CharField(max_length=100)
    reference_id = models.CharField(max_length=255)
    kind = models.CharField(max_length=50)

    class Meta:
        db_table = "workflow_xero_error"
        verbose_name = "Xero Error"
        verbose_name_plural = "Xero Errors"
