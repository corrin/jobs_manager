import uuid
from django.db import models
from django.utils import timezone


class XeroAccount(models.Model):
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )  # Internal UUID
    xero_id = models.UUIDField(
        unique=True, null=False, blank=False
    )  # Xero's UUID for the account, required
    account_code = models.CharField(
        max_length=20, null=True, blank=True
    )  # Optional since some accounts don't have codes
    account_name = models.CharField(max_length=255, null=False, blank=False)  # Required
    description = models.TextField(null=True, blank=True)
    account_type = models.CharField(
        max_length=50, null=True, blank=True
    )  # For account type enum values
    tax_type = models.CharField(max_length=50, null=True, blank=True)  # For tax type
    enable_payments = models.BooleanField(
        default=False
    )  # Boolean for enable payments to account
    xero_last_modified = models.DateTimeField(null=False, blank=False)
    xero_last_synced = models.DateTimeField(null=True, blank=True, default=timezone.now)
    raw_json = models.JSONField()  # Store the raw API response for reference
    django_created_at = models.DateTimeField(auto_now_add=True)
    django_updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.account_name} ({self.account_code})"
