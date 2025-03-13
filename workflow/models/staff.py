from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, ClassVar, List, Optional, cast

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.timezone import now as timezone_now
from simple_history.models import HistoricalRecords  # type: ignore


class StaffManager(BaseUserManager):
    def create_user(
        self, email: str, password: Optional[str] = None, **extra_fields: Any
    ) -> "Staff":
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = cast(Staff, self.model(email=email, **extra_fields))
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
        self, email: str, password: Optional[str] = None, **extra_fields: Any
    ) -> "Staff":
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("wage_rate", 0)
        # extra_fields.setdefault("charge_out_rate", 0)
        return self.create_user(email, password, **extra_fields)


class Staff(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )  # type: ignore
    password_needs_reset: bool = models.BooleanField(default=False)  # type: ignore
    email: str = models.EmailField(unique=True)  # type: ignore
    first_name: str = models.CharField(max_length=30)  # type: ignore
    last_name: str = models.CharField(max_length=30)  # type: ignore
    preferred_name: Optional[str] = models.CharField(
        max_length=30, blank=True, null=True
    )  # type: ignore
    wage_rate: float = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )  # type: ignore

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

    ims_payroll_id: str = models.CharField(max_length=100, unique=True, null=True, blank=True)  # type: ignore
    is_active: bool = models.BooleanField(default=True)  # type: ignore
    is_staff: bool = models.BooleanField(default=False)  # type: ignore
    date_joined: datetime = models.DateTimeField(default=timezone.now)  # type: ignore
    raw_ims_data = models.JSONField(null=True, blank=True, default=dict)  # type: ignore
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    history: HistoricalRecords = HistoricalRecords()  # type: ignore

    objects = StaffManager()  # Use the custom manager

    USERNAME_FIELD: str = "email"
    REQUIRED_FIELDS: ClassVar[List[str]] = [
        "first_name",
        "last_name",
        # "charge_out_rate",
    ]

    class Meta:
        ordering = ["last_name", "first_name"]

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
