"""Timesheet pay run cache model."""

from __future__ import annotations

from django.db import models


class XeroPayRun(models.Model):
    """Persisted snapshot of a Xero Payroll pay run."""

    pay_run_id = models.UUIDField(unique=True)
    payroll_calendar_id = models.UUIDField(null=True, blank=True)
    period_start_date = models.DateField()
    period_end_date = models.DateField()
    payment_date = models.DateField(null=True, blank=True)
    pay_run_status = models.CharField(max_length=32)
    pay_run_type = models.CharField(max_length=32, null=True, blank=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-period_start_date", "-updated_at"]
        indexes = [
            models.Index(fields=["period_start_date"]),
            models.Index(fields=["pay_run_status"]),
        ]

    def __str__(self) -> str:
        return f"PayRun {self.pay_run_id} ({self.period_start_date} - {self.period_end_date})"

    def to_payload(self) -> dict:
        return {
            "pay_run_id": str(self.pay_run_id),
            "payroll_calendar_id": (
                str(self.payroll_calendar_id) if self.payroll_calendar_id else None
            ),
            "period_start_date": self.period_start_date,
            "period_end_date": self.period_end_date,
            "payment_date": self.payment_date,
            "pay_run_status": self.pay_run_status,
            "pay_run_type": self.pay_run_type,
        }
