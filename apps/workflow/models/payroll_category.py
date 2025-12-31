from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from django.db import models

if TYPE_CHECKING:
    from apps.job.models import Job


class PayrollCategory(models.Model):
    """
    Maps leave jobs and work rates to Xero payroll posting.

    Each row defines either:
    - A leave type (linked to Job via Job.payroll_category FK)
    - A work rate type (matched by rate_multiplier on time entries)

    The xero_name is used for:
    - Display in the UI
    - Looking up the Xero Leave Type ID or Earnings Rate ID at runtime
    """

    xero_name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Xero name for lookup (Leave Type name or Earnings Rate name)",
    )

    uses_leave_api = models.BooleanField(
        default=False,
        help_text="True = use Xero Leave API. False = use Xero Timesheets API.",
    )

    rate_multiplier = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
        help_text="Rate multiplier for work entries (e.g., 1.0, 1.5, 2.0). "
        "NULL for leave categories.",
    )

    class Meta:
        verbose_name = "Payroll Category"
        verbose_name_plural = "Payroll Categories"
        ordering = ["xero_name"]

    def __str__(self) -> str:
        return self.xero_name

    @classmethod
    def get_for_job(cls, job: "Job") -> Optional["PayrollCategory"]:
        """
        Get the PayrollCategory for a job.

        For leave jobs: returns job.payroll_category (direct FK)
        For regular jobs: returns None (work entries use rate_multiplier matching)
        """
        return job.payroll_category

    @classmethod
    def get_for_rate_multiplier(
        cls, multiplier: Decimal
    ) -> Optional["PayrollCategory"]:
        """
        Get the PayrollCategory for a work entry based on rate multiplier.

        Returns None if no matching category found.
        """
        return cls.objects.filter(rate_multiplier=multiplier).first()
