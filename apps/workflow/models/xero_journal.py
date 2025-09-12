import uuid

from django.db import models
from django.utils import timezone


class XeroJournal(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    xero_id = models.UUIDField(unique=True)
    xero_tenant_id = models.CharField(
        max_length=255, null=True, blank=True
    )  # For reference only - we are not fully multi-tenant yet
    # The JournalDate from Xero is generally a date-only field.
    journal_date = models.DateField()
    # CreatedDateUTC is typically a datetime from Xero
    created_date_utc = models.DateTimeField()
    journal_number = models.IntegerField(null=False, blank=False, unique=True)
    reference = models.CharField(max_length=255, null=True, blank=True)
    source_id = models.UUIDField(null=True, blank=True)
    source_type = models.CharField(max_length=50, null=True, blank=True)
    raw_json = models.JSONField()
    xero_last_modified = models.DateTimeField()
    django_created_at = models.DateTimeField(auto_now_add=True)
    django_updated_at = models.DateTimeField(auto_now=True)
    xero_last_synced = models.DateTimeField(null=True, blank=True, default=timezone.now)

    def __str__(self):
        # Display the journal number if available, otherwise fallback to xero_id
        return f"Journal {self.journal_number or self.xero_id}"


class XeroJournalLineItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Each journal can have multiple line items
    journal = models.ForeignKey(
        XeroJournal, on_delete=models.CASCADE, related_name="line_items"
    )
    xero_line_id = models.UUIDField(unique=True)
    # Link to XeroAccount if possible. If it gets deleted or not found,
    # we keep the line item as historical data.
    account = models.ForeignKey(
        "XeroAccount", on_delete=models.SET_NULL, null=True, blank=True
    )
    description = models.TextField(null=True, blank=True)
    # Typically journals contain both credit and debit lines.
    # Net/Gross/Tax amounts might be needed.
    net_amount = models.DecimalField(max_digits=10, decimal_places=2)
    gross_amount = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2)
    tax_type = models.CharField(max_length=50, null=True, blank=True)
    tax_name = models.CharField(max_length=255, null=True, blank=True)
    raw_json = models.JSONField()
    django_created_at = models.DateTimeField(auto_now_add=True)
    django_updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"JournalLineItem {self.xero_line_id}"
