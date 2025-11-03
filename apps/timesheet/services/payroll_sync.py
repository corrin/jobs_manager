"""Xero Payroll Sync Service.

Service for posting weekly timesheets to Xero Payroll NZ.
"""

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List
from uuid import UUID

from apps.accounts.models import Staff
from apps.job.models.costing import CostLine
from apps.workflow.api.xero.payroll import create_employee_leave, post_timesheet
from apps.workflow.models import CompanyDefaults
from apps.workflow.services.error_persistence import persist_app_error

logger = logging.getLogger("timesheet.payroll")


class PayrollSyncService:
    """Service for syncing timesheet data to Xero Payroll."""

    @classmethod
    def post_week_to_xero(cls, staff_id: UUID, week_start_date: date) -> Dict[str, Any]:
        """
        Post a week's timesheet to Xero Payroll for a specific staff member.

        Args:
            staff_id: UUID of the staff member
            week_start_date: Monday of the week to post (must be a Monday)

        Returns:
            Dict containing:
                - success (bool): Whether the post was successful
                - xero_timesheet_id (str): Xero timesheet ID if successful
                - entries_posted (int): Number of entries posted
                - leave_hours (Decimal): Total leave hours
                - work_hours (Decimal): Total work hours
                - errors (List[str]): Any errors encountered

        Raises:
            ValueError: If inputs are invalid
            Exception: If Xero API call fails
        """
        # Validate inputs
        if week_start_date.weekday() != 0:
            raise ValueError("week_start_date must be a Monday")

        try:
            # Get staff and validate xero_user_id
            staff = Staff.objects.get(id=staff_id)
            if not staff.xero_user_id:
                raise ValueError(
                    f"Staff member {staff.email} does not have a xero_user_id configured"
                )

            # Calculate week end date (Sunday)
            week_end_date = week_start_date + timedelta(days=6)

            logger.info(
                f"Collecting timesheet entries for {staff.email} "
                f"from {week_start_date} to {week_end_date}"
            )

            # Collect time entries for the week
            time_entries = CostLine.objects.filter(
                kind="time",
                accounting_date__gte=week_start_date,
                accounting_date__lte=week_end_date,
            ).select_related("cost_set__job")

            # Filter to entries for this staff
            staff_entries = [
                entry
                for entry in time_entries
                if entry.meta.get("staff_id") == str(staff_id)
            ]

            if not staff_entries:
                logger.warning(
                    f"No timesheet entries found for {staff.email} "
                    f"in week {week_start_date}"
                )
                return {
                    "success": True,
                    "xero_timesheet_id": None,
                    "entries_posted": 0,
                    "leave_hours": Decimal("0"),
                    "work_hours": Decimal("0"),
                    "errors": [],
                }

            # Get company defaults for mappings
            company_defaults = CompanyDefaults.get_instance()

            # Categorize entries
            leave_entries, work_entries = cls._categorize_entries(staff_entries)

            xero_employee_id = UUID(staff.xero_user_id)
            xero_timesheet_id = None
            leave_ids = []

            # Post work entries as timesheet
            if work_entries:
                timesheet_lines = cls._map_work_entries(work_entries, company_defaults)
                logger.info(
                    f"Posting {len(timesheet_lines)} work entries to Xero timesheet"
                )

                timesheet = post_timesheet(
                    employee_id=xero_employee_id,
                    week_start_date=week_start_date,
                    timesheet_lines=timesheet_lines,
                )
                xero_timesheet_id = str(timesheet.timesheet_id)
                logger.info(f"Successfully posted timesheet {xero_timesheet_id}")

            # Post leave entries using Leave API
            if leave_entries:
                leave_ids = cls._post_leave_entries(
                    xero_employee_id, leave_entries, company_defaults
                )
                logger.info(f"Successfully posted {len(leave_ids)} leave records")

            # Calculate totals
            work_hours = sum(Decimal(str(entry.quantity)) for entry in work_entries)
            leave_hours = sum(Decimal(str(entry.quantity)) for entry in leave_entries)

            return {
                "success": True,
                "xero_timesheet_id": xero_timesheet_id,
                "xero_leave_ids": leave_ids,
                "entries_posted": len(staff_entries),
                "leave_hours": leave_hours,
                "work_hours": work_hours,
                "errors": [],
            }

        except Exception as exc:
            logger.error(
                f"Failed to post timesheet for staff {staff_id}: {exc}", exc_info=True
            )
            persist_app_error(exc)
            return {
                "success": False,
                "xero_timesheet_id": None,
                "entries_posted": 0,
                "leave_hours": Decimal("0"),
                "work_hours": Decimal("0"),
                "errors": [str(exc)],
            }

    @classmethod
    def _categorize_entries(
        cls, entries: List[CostLine]
    ) -> tuple[List[CostLine], List[CostLine]]:
        """
        Categorize cost line entries into leave vs work.

        Args:
            entries: List of CostLine entries to categorize

        Returns:
            Tuple of (leave_entries, work_entries)
        """
        leave_entries = []
        work_entries = []

        for entry in entries:
            job = entry.cost_set.job
            leave_type = job.get_leave_type()

            if leave_type != "N/A":
                leave_entries.append(entry)
            else:
                work_entries.append(entry)

        return leave_entries, work_entries

    @classmethod
    def _map_work_entries(
        cls, entries: List[CostLine], company_defaults: CompanyDefaults
    ) -> List[Dict[str, Any]]:
        """
        Map work CostLine entries to Xero Payroll timesheet lines format.

        Args:
            entries: List of work CostLine entries
            company_defaults: CompanyDefaults instance with earnings rate mappings

        Returns:
            List of timesheet line dictionaries for Xero API
        """
        timesheet_lines = []

        for entry in entries:
            rate_multiplier = entry.meta.get("wage_rate_multiplier", 1.0)

            # Map rate_multiplier to earnings rate field
            rate_mapping = {
                2.0: ("xero_double_time_earnings_rate_id", "Double time"),
                1.5: ("xero_time_half_earnings_rate_id", "Time and a half"),
                1.0: ("xero_ordinary_earnings_rate_id", "Ordinary time"),
            }

            field_name, rate_name = rate_mapping.get(
                rate_multiplier, ("xero_ordinary_earnings_rate_id", "Ordinary time")
            )
            earnings_rate_id = getattr(company_defaults, field_name)

            if not earnings_rate_id:
                raise ValueError(
                    f"{rate_name} earnings rate not configured. "
                    "Run: python manage.py configure_xero_payroll --configure"
                )

            timesheet_lines.append(
                {
                    "date": entry.accounting_date,
                    "earnings_rate_id": earnings_rate_id,
                    "number_of_units": float(entry.quantity),
                }
            )

        return timesheet_lines

    @classmethod
    def _post_leave_entries(
        cls,
        employee_id: UUID,
        entries: List[CostLine],
        company_defaults: CompanyDefaults,
    ) -> List[str]:
        """
        Post leave CostLine entries to Xero using the Leave API.

        Groups consecutive days of the same leave type together.

        Args:
            employee_id: Xero employee ID
            entries: List of leave CostLine entries
            company_defaults: CompanyDefaults instance with leave type ID mappings

        Returns:
            List of leave IDs created in Xero
        """
        # Map leave type to leave_type_id field
        leave_mapping = {
            "annual": ("xero_annual_leave_type_id", "Annual leave"),
            "sick": ("xero_sick_leave_type_id", "Sick leave"),
            "other": ("xero_other_leave_type_id", "Other leave"),
            "unpaid": ("xero_unpaid_leave_type_id", "Unpaid leave"),
        }

        # Group entries by leave type and sort by date
        from collections import defaultdict

        grouped = defaultdict(list)
        for entry in entries:
            job = entry.cost_set.job
            leave_type = job.get_leave_type()

            if leave_type not in leave_mapping:
                raise ValueError(f"Unknown leave type: {leave_type}")

            grouped[leave_type].append(entry)

        # Sort each group by date
        for leave_type in grouped:
            grouped[leave_type].sort(key=lambda e: e.accounting_date)

        leave_ids = []

        # Process each leave type
        for leave_type, type_entries in grouped.items():
            field_name, leave_name = leave_mapping[leave_type]
            leave_type_id = getattr(company_defaults, field_name)

            if not leave_type_id:
                raise ValueError(
                    f"{leave_name} type ID not configured. "
                    "Run: python manage.py interact_with_xero --configure-payroll"
                )

            # Group consecutive days together
            if not type_entries:
                continue

            current_start = type_entries[0].accounting_date
            current_end = type_entries[0].accounting_date
            current_hours = float(type_entries[0].quantity)

            for i in range(1, len(type_entries)):
                entry = type_entries[i]
                expected_next = current_end + timedelta(days=1)

                # Check if consecutive and same hours per day
                if (
                    entry.accounting_date == expected_next
                    and abs(float(entry.quantity) - current_hours) < 0.01
                ):
                    # Extend current range
                    current_end = entry.accounting_date
                else:
                    # Create leave for current range
                    leave_id = create_employee_leave(
                        employee_id=employee_id,
                        leave_type_id=leave_type_id,
                        start_date=current_start,
                        end_date=current_end,
                        hours_per_day=current_hours,
                        description=f"{leave_name}",
                    )
                    leave_ids.append(leave_id)

                    # Start new range
                    current_start = entry.accounting_date
                    current_end = entry.accounting_date
                    current_hours = float(entry.quantity)

            # Create leave for final range
            leave_id = create_employee_leave(
                employee_id=employee_id,
                leave_type_id=leave_type_id,
                start_date=current_start,
                end_date=current_end,
                hours_per_day=current_hours,
                description=f"{leave_name}",
            )
            leave_ids.append(leave_id)

        return leave_ids
