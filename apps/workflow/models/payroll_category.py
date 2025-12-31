from typing import TYPE_CHECKING, Optional

from django.db import models

if TYPE_CHECKING:
    from apps.job.models import Job


class PayrollCategory(models.Model):
    """
    Maps job types and work rates to Xero payroll posting behavior.

    Each row defines either:
    - A leave type (matched by job_name_pattern in the job name)
    - A work rate type (matched by rate_multiplier on the time entry)

    This centralizes all the mapping logic that was previously scattered across
    payroll.py categorization functions and CompanyDefaults Xero ID fields.
    """

    name = models.CharField(
        max_length=50,
        unique=True,
        help_text="Internal identifier (e.g., 'annual_leave', 'work_ordinary')",
    )
    display_name = models.CharField(
        max_length=100,
        help_text="Human-readable name (e.g., 'Annual Leave', 'Ordinary Time')",
    )

    # Matching criteria - use ONE of these, not both
    job_name_pattern = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Substring to match in job name (e.g., 'annual leave'). "
        "Case-insensitive. Leave blank for work rate categories.",
    )
    rate_multiplier = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
        help_text="Rate multiplier for work entries (e.g., 1.0, 1.5, 2.0). "
        "Leave blank for leave type categories.",
    )

    # Posting behavior
    uses_leave_api = models.BooleanField(
        default=False,
        help_text="True = use Xero Leave API (for leave with balances). "
        "False = use Xero Timesheets API.",
    )

    # Xero identifiers - both are names, looked up at runtime to get IDs
    xero_leave_type_name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Xero Leave Type name (looked up at runtime to get ID). "
        "Required if uses_leave_api=True.",
    )
    xero_earnings_rate_name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Xero Earnings Rate name (looked up at runtime to get ID). "
        "Required if uses_leave_api=False (work entries).",
    )

    class Meta:
        verbose_name = "Payroll Category"
        verbose_name_plural = "Payroll Categories"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.display_name

    @classmethod
    def get_for_job(cls, job: "Job") -> Optional["PayrollCategory"]:
        """
        Get the PayrollCategory for a job based on job name pattern matching.

        Returns None if the job doesn't match any leave/special category
        (i.e., it's regular work).
        """
        normalized_name = job.name.strip().lower()

        for category in cls.objects.filter(job_name_pattern__isnull=False):
            if category.job_name_pattern.lower() in normalized_name:
                return category

        return None
