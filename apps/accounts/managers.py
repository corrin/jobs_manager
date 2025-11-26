from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any, Optional

from django.contrib.auth.base_user import BaseUserManager
from django.db import models
from django.utils import timezone

if TYPE_CHECKING:
    from apps.accounts.models import Staff

    BaseManagerClass = BaseUserManager["Staff"]
else:
    BaseManagerClass = BaseUserManager


class StaffManager(BaseManagerClass):
    """
    Custom manager for Staff user model that combines:
    - Type hints for better code maintainability
    - Strict validation for superuser creation
    - Proper default values for staff-specific fields
    """

    def create_user(
        self, email: str, password: Optional[str] = None, **extra_fields: Any
    ) -> "Staff":
        if not email:
            raise ValueError("The Email field must be set")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
        self, email: str, password: str, **extra_fields: Any
    ) -> "Staff":
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("wage_rate", 0)  # Default wage rate for superusers

        # Strict validation for superuser status
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)

    def active_on_date(self, target_date: date) -> models.QuerySet["Staff"]:
        """Get staff members who were employed on a specific date."""
        return self.filter(date_joined__date__lte=target_date).filter(
            models.Q(date_left__isnull=True) | models.Q(date_left__gt=target_date)
        )

    def currently_active(self) -> models.QuerySet["Staff"]:
        """Get currently active staff (replaces is_active=True filters)"""
        return self.active_on_date(timezone.now().date())

    def active_between_dates(
        self, start_date: date, end_date: date
    ) -> models.QuerySet["Staff"]:
        """Get staff members who were employed at any point during the date range."""
        return self.filter(date_joined__date__lte=end_date).filter(
            models.Q(date_left__isnull=True) | models.Q(date_left__gte=start_date)
        )
