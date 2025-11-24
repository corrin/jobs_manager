from typing import Any, Tuple

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.workflow.api.xero.constants import XERO_SCOPES


class XeroToken(models.Model):
    tenant_id = models.CharField(max_length=100, unique=True)
    token_type = models.CharField(max_length=50)
    access_token = models.TextField()
    refresh_token = models.TextField()
    expires_at = models.DateTimeField()
    scope = models.TextField(default=" ".join(XERO_SCOPES))

    def __str__(self) -> str:
        return f"Xero Token for Tenant: {self.tenant_id}"

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at

    # Enforce singleton behavior
    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self.pk and XeroToken.objects.exists():
            raise ValidationError("There can be only one XeroToken instance")
        super().save(*args, **kwargs)

    @classmethod
    def get_instance(cls) -> Tuple["XeroToken", bool]:
        # Ensures that there's always one XeroToken instance
        instance, created = cls.objects.get_or_create(
            id=1
        )  # Always use id=1 for simplicity
        return instance
