"""Helpers for linking Staff records with Xero Payroll employees."""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from django.db import transaction

from apps.accounts.models import Staff
from apps.workflow.api.xero.payroll import create_payroll_employee, get_employees

logger = logging.getLogger("timesheet.payroll")


class PayrollEmployeeSyncService:
    """Service class used by management commands to sync staff with Xero Payroll."""

    DATE_FORMATS: Sequence[str] = (
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%d/%m/%Y",
        "%d/%m/%y",
    )
    DEFAULT_COUNTRY: str = "New Zealand"

    @classmethod
    def sync_staff(
        cls,
        staff_queryset: Optional[Iterable[Staff]] = None,
        *,
        dry_run: bool = False,
        allow_create: bool = False,
    ) -> Dict[str, Any]:
        """
        Link Staff rows with Xero Payroll employees and optionally create missing employees.

        Args:
            staff_queryset: Optional iterable of Staff objects to limit the operation.
            dry_run: When True, show the planned actions without mutating Xero or the DB.
            allow_create: When True, create payroll employees when no match is found.

        Returns:
            Summary dictionary describing what happened (or would happen in dry-run mode).
        """
        if staff_queryset is None:
            staff_queryset = Staff.objects.filter(date_left__isnull=True)

        staff_members = list(staff_queryset)

        summary: Dict[str, Any] = {
            "total": len(staff_members),
            "linked": [],
            "created": [],
            "already_linked": [],
            "missing": [],
            "dry_run": dry_run,
            "allow_create": allow_create,
        }

        if not staff_members:
            return summary

        xero_employees = get_employees()
        employee_index = cls._index_xero_employees(xero_employees)

        matched_staff: List[Tuple[Staff, Dict[str, Optional[str]]]] = []
        missing_staff: List[Staff] = []

        for staff in staff_members:
            if staff.xero_user_id:
                summary["already_linked"].append(cls._format_staff(staff))
                continue

            match = cls._match_staff_to_employee(staff, employee_index)
            if match:
                matched_staff.append((staff, match))
            else:
                missing_staff.append(staff)

        creation_payloads: List[Tuple[Staff, Dict[str, Any]]] = []
        if allow_create and missing_staff:
            creation_payloads = [
                (staff, cls._build_employee_payload(staff)) for staff in missing_staff
            ]

        if dry_run:
            summary["linked"] = [
                cls._summarize_link(staff, match["employee_id"], match)
                for staff, match in matched_staff
            ]
            summary["created"] = [
                cls._summarize_link(staff, None, None) for staff, _ in creation_payloads
            ]
            summary["missing"] = (
                []
                if allow_create
                else [cls._format_staff(staff) for staff in missing_staff]
            )
            return summary

        for staff, match in matched_staff:
            employee_id = match.get("employee_id")
            if not employee_id:
                raise ValueError(
                    f"Xero employee match for {staff.email} is missing employee_id"
                )
            cls._link_staff(staff, employee_id)
            summary["linked"].append(cls._summarize_link(staff, employee_id, match))

        if allow_create:
            for staff, payload in creation_payloads:
                employee = create_payroll_employee(payload)
                employee_id = str(employee.employee_id)
                cls._link_staff(staff, employee_id)
                summary["created"].append(
                    cls._summarize_link(
                        staff,
                        employee_id,
                        {
                            "employee_id": employee_id,
                            "first_name": employee.first_name,
                            "last_name": employee.last_name,
                            "email": (employee.email or "").lower() or None,
                        },
                    )
                )
            summary["missing"] = []
        else:
            summary["missing"] = [cls._format_staff(staff) for staff in missing_staff]

        return summary

    @classmethod
    def _link_staff(cls, staff: Staff, employee_id: str) -> None:
        logger.info("Linking staff %s to Xero employee %s", staff.email, employee_id)
        staff.xero_user_id = employee_id
        with transaction.atomic():
            staff.save(update_fields=["xero_user_id", "updated_at"])

    @classmethod
    def _index_xero_employees(
        cls, employees: Sequence[Any]
    ) -> Dict[str, Dict[str, Dict[str, Optional[str]]]]:
        by_email: Dict[str, Dict[str, Optional[str]]] = {}
        by_name: Dict[Tuple[str, str], Dict[str, Optional[str]]] = {}

        for employee in employees:
            serialized = cls._serialize_employee(employee)
            first_name = serialized["first_name"] or ""
            last_name = serialized["last_name"] or ""
            name_key = (first_name.lower(), last_name.lower())

            if serialized["email"]:
                by_email.setdefault(serialized["email"], serialized)

            if name_key not in by_name:
                by_name[name_key] = serialized

        return {"by_email": by_email, "by_name": by_name}

    @classmethod
    def _match_staff_to_employee(
        cls, staff: Staff, index: Dict[str, Dict[Any, Dict[str, Optional[str]]]]
    ) -> Optional[Dict[str, Optional[str]]]:
        email = (staff.email or "").strip().lower()
        if email and email in index["by_email"]:
            return index["by_email"][email]

        name_key = (
            (staff.first_name or "").strip().lower(),
            (staff.last_name or "").strip().lower(),
        )
        return index["by_name"].get(name_key)

    @classmethod
    def _serialize_employee(cls, employee: Any) -> Dict[str, Optional[str]]:
        employee_id = getattr(employee, "employee_id", None)
        first_name = getattr(employee, "first_name", "") or ""
        last_name = getattr(employee, "last_name", "") or ""
        email = getattr(employee, "email", "") or ""

        return {
            "employee_id": str(employee_id) if employee_id else None,
            "first_name": first_name.strip(),
            "last_name": last_name.strip(),
            "email": email.strip().lower() if email else None,
        }

    @classmethod
    def _build_employee_payload(cls, staff: Staff) -> Dict[str, Any]:
        ims_data = staff.raw_ims_data or {}

        first_name = cls._clean_string(staff.first_name, 35)
        last_name = cls._clean_string(staff.last_name, 35)
        email = cls._clean_string(staff.email, 255)
        if not first_name or not last_name or not email:
            raise ValueError(
                f"Staff {staff.id} is missing first name, last name, or email"
            )

        date_of_birth = cls._parse_date(
            ims_data.get("BirthDate") or ims_data.get("Birthdate")
        )
        if not date_of_birth:
            raise ValueError(f"Staff {staff.email} is missing a BirthDate value")

        address_line1 = cls._clean_string(
            cls._first_value(
                ims_data,
                [
                    "PostalAddress1",
                    "ResidentialAddress1",
                    "HomeAddress1",
                ],
            ),
            35,
        )
        city = cls._clean_string(
            cls._first_value(
                ims_data,
                [
                    "PostalAddress2",
                    "ResidentialAddress2",
                    "City",
                ],
            ),
            50,
        )
        post_code = cls._clean_string(
            cls._first_value(
                ims_data,
                [
                    "PostalAddress3",
                    "ResidentialPostCode",
                    "Postcode",
                ],
            ),
            8,
        )

        if not address_line1 or not city or not post_code:
            raise ValueError(
                f"Staff {staff.email} is missing required address details "
                f"(line1={address_line1}, city={city}, post_code={post_code})"
            )

        phone_number = cls._clean_string(
            cls._first_value(
                ims_data,
                [
                    "MobilePhone",
                    "HomePhone",
                    "HomePhone2",
                ],
            ),
            20,
        )

        start_date = cls._parse_date(ims_data.get("StartDate"))
        job_title = cls._clean_string(
            cls._first_value(
                ims_data,
                [
                    "Position",
                    "Title",
                    "JobTitle",
                ],
            ),
            50,
        )

        payload: Dict[str, Any] = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "date_of_birth": date_of_birth,
            "start_date": start_date,
            "phone_number": phone_number,
            "job_title": job_title,
            "address": {
                "address_line1": address_line1,
                "address_line2": cls._clean_string(
                    cls._first_value(
                        ims_data,
                        [
                            "PostalAddressExtra",
                            "ResidentialAddress3",
                            "HomeAddress2",
                        ],
                    ),
                    35,
                ),
                "city": city,
                "post_code": post_code,
                "suburb": cls._clean_string(ims_data.get("Suburb"), 35),
                "country_name": cls._clean_string(
                    ims_data.get("Country") or ims_data.get("CountryName"), 50
                )
                or cls.DEFAULT_COUNTRY,
            },
        }

        return payload

    @classmethod
    def _parse_date(cls, value: Any) -> Optional[date]:
        if not value:
            return None
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value

        value_str = str(value).strip()
        for fmt in cls.DATE_FORMATS:
            try:
                return datetime.strptime(value_str, fmt).date()
            except ValueError:
                continue

        try:
            # Last resort - leverage fromisoformat for odd inputs
            return datetime.fromisoformat(value_str).date()
        except ValueError:
            raise ValueError(f"Unable to parse date value '{value_str}'") from None

    @staticmethod
    def _format_staff(staff: Staff) -> Dict[str, Any]:
        return {
            "staff_id": str(staff.id),
            "email": staff.email,
            "first_name": staff.first_name,
            "last_name": staff.last_name,
        }

    @staticmethod
    def _summarize_link(
        staff: Staff,
        employee_id: Optional[str],
        match: Optional[Dict[str, Optional[str]]],
    ) -> Dict[str, Any]:
        summary = PayrollEmployeeSyncService._format_staff(staff)
        summary.update(
            {
                "xero_employee_id": employee_id,
                "xero_email": match.get("email") if match else None,
                "xero_name": (
                    f"{match.get('first_name', '')} {match.get('last_name', '')}".strip()
                    if match
                    else None
                ),
            }
        )
        return summary

    @staticmethod
    def _first_value(data: Dict[str, Any], keys: Sequence[str]) -> Optional[str]:
        for key in keys:
            value = data.get(key)
            if value not in (None, "", []):
                return str(value)
        return None

    @staticmethod
    def _clean_string(
        value: Optional[str], max_length: Optional[int] = None
    ) -> Optional[str]:
        if value is None:
            return None
        cleaned = str(value).strip()
        if not cleaned:
            return None
        if max_length is not None:
            return cleaned[:max_length]
        return cleaned
