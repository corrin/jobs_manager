import uuid
from datetime import date, datetime
from typing import ClassVar, List, Optional

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.timezone import now as timezone_now
from simple_history.models import HistoricalRecords

from .managers import StaffManager


class Staff(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    icon = models.ImageField(upload_to="staff_icons/", null=True, blank=True)
    password_needs_reset: bool = models.BooleanField(default=False)
    email: str = models.EmailField(unique=True)
    first_name: str = models.CharField(max_length=30)
    last_name: str = models.CharField(max_length=30)
    preferred_name: Optional[str] = models.CharField(
        max_length=30, blank=True, null=True
    )
    wage_rate: float = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    ims_payroll_id: str = models.CharField(
        max_length=100, unique=True, null=True, blank=True
    )
    raw_ims_data = models.JSONField(null=True, blank=True, default=dict)
    is_active: bool = models.BooleanField(default=True)
    is_staff: bool = models.BooleanField(default=False)
    date_joined: datetime = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    hours_mon = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=8.00,
        help_text="Standard hours for Monday, 0 for non-working day",
    )
    hours_tue = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=8.00,
        help_text="Standard hours for Tuesday, 0 for non-working day",
    )
    hours_wed = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=8.00,
        help_text="Standard hours for Wednesday, 0 for non-working day",
    )
    hours_thu = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=8.00,
        help_text="Standard hours for Thursday, 0 for non-working day",
    )
    hours_fri = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=8.00,
        help_text="Standard hours for Friday, 0 for non-working day",
    )
    hours_sat = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0.00,
        help_text="Standard hours for Saturday, 0 for non-working day",
    )
    hours_sun = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0.00,
        help_text="Standard hours for Sunday, 0 for non-working day",
    )

    history: HistoricalRecords = HistoricalRecords(
        table_name="workflow_historicalstaff"
    )

    objects = StaffManager()

    USERNAME_FIELD: str = "email"
    REQUIRED_FIELDS: ClassVar[List[str]] = [
        "first_name",
        "last_name",
    ]

    class Meta:
        ordering = ["last_name", "first_name"]
        db_table = "workflow_staff"
        verbose_name = "Staff Member"
        verbose_name_plural = "Staff Members"

    def save(self, *args, **kwargs):
        # We have to do this because fixtures don't have updated_at,
        # so auto_now_add doesn't work
        self.updated_at = timezone_now()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def get_scheduled_hours(self, target_date: date) -> float:
        """Get expected working hours for a specific date"""
        weekday = target_date.weekday()
        hours_by_day = [
            self.hours_mon,
            self.hours_tue,
            self.hours_wed,
            self.hours_thu,
            self.hours_fri,
            self.hours_sat,
            self.hours_sun,
        ]
        return float(hours_by_day[weekday])

    def get_display_name(self) -> str:
        display = self.preferred_name or self.first_name
        display = display.split()[0] if display else ""
        return display

    def get_display_full_name(self) -> str:
        display = self.get_display_name() + " " + self.last_name
        return display

    def is_staff_manager(self):
        return self.groups.filter(name="StaffManager").exists() or self.is_superuser

    @property
    def name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @name.setter
    def name(self, value: str) -> None:
        parts = value.split()
        if len(parts) >= 2:
            self.first_name = parts[0]
            self.last_name = " ".join(parts[1:])
        else:
            raise ValueError("Name must include both first and last name")
