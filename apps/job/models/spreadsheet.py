import uuid

from django.db import models


class QuoteSpreadsheet(models.Model):
    """
    Model to represent a spreadsheet for job quotes.
    This model is used to link a Google Sheets document to a job.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sheet_id = models.CharField(max_length=100, help_text="Google Drive file ID")
    sheet_url = models.URLField(max_length=500, blank=True, null=True)
    tab = models.CharField(
        max_length=100, blank=True, null=True, default="Primary Details"
    )
    job = models.OneToOneField(
        "Job",
        on_delete=models.CASCADE,
        related_name="quote_sheet",
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = "Quote Spreadsheet"
        verbose_name_plural = "Quote Spreadsheets"

    def __str__(self):
        return f"Quote Spreadsheet for Job {self.job.job_number}\nID: {self.sheet_id}\nURL: {self.sheet_url}\n{'-' * 40}"
