"""
Modern Timesheet REST Views

REST views for the modern timesheet system using CostLine architecture.
Provides a bridge between legacy TimeEntry system and modern CostLine system.
"""

import logging
from decimal import Decimal

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Staff
from apps.job.models import CostLine, Job
from apps.job.serializers.costing_serializer import (
    CostLineSerializer,
    TimesheetCostLineSerializer,
)
from apps.job.services.timesheet_migration_service import TimesheetToCostLineService

logger = logging.getLogger(__name__)


class ModernTimesheetEntryView(APIView):
    """
    Modern timesheet entry management using CostLine architecture

    GET /job/rest/timesheet/entries/?staff_id=<uuid>&date=<date>
    POST /job/rest/timesheet/entries/
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get timesheet entries (CostLines) for a specific staff member and date"""
        staff_id = request.query_params.get("staff_id")
        entry_date = request.query_params.get("date")

        # Guard clauses for validation
        if not staff_id:
            return Response(
                {"error": "staff_id is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        if not entry_date:
            return Response(
                {"error": "date is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Validate staff exists
        try:
            staff = Staff.objects.get(id=staff_id)
        except Staff.DoesNotExist:
            return Response(
                {"error": "Staff member not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Validate date format
        parsed_date = parse_date(entry_date)
        if not parsed_date:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:  # Query CostLines with kind='time' for the staff/date
            # Using JSON field queries for metadata (MySQL compatible)
            cost_lines = (
                CostLine.objects.filter(
                    kind="time",
                    meta__contains={
                        "staff_id": str(staff_id),
                        "date": parsed_date.isoformat(),
                    },
                )
                .select_related("cost_set__job__client")
                .order_by("id")
            )

            # Calculate totals
            total_hours = sum(float(line.quantity) for line in cost_lines)
            billable_hours = sum(
                float(line.quantity)
                for line in cost_lines
                if line.meta.get("is_billable", True)
            )
            total_cost = sum(line.total_cost for line in cost_lines)
            total_revenue = sum(line.total_rev for line in cost_lines)

            # Serialize the results using timesheet-specific serializer
            serializer = TimesheetCostLineSerializer(cost_lines, many=True)

            return Response(
                {
                    "cost_lines": serializer.data,
                    "staff": {
                        "id": str(staff.id),
                        "name": staff.get_display_name(),
                        "firstName": staff.first_name,
                        "lastName": staff.last_name,
                    },
                    "date": entry_date,
                    "summary": {
                        "total_hours": total_hours,
                        "billable_hours": billable_hours,
                        "non_billable_hours": total_hours - billable_hours,
                        "total_cost": float(total_cost),
                        "total_revenue": float(total_revenue),
                        "entry_count": cost_lines.count(),
                    },
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(
                f"Error fetching timesheet entries for staff {staff_id}, date {entry_date}: {e}"
            )
            return Response(
                {"error": "Failed to fetch timesheet entries"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def post(self, request):
        """Create a timesheet entry as a CostLine in the actual CostSet"""
        try:
            data = request.data

            # Validate required fields with guard clauses
            job_id = data.get("job_id")
            if not job_id:
                return Response(
                    {"error": "job_id is required"}, status=status.HTTP_400_BAD_REQUEST
                )

            staff_id = data.get("staff_id")
            if not staff_id:
                return Response(
                    {"error": "staff_id is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            hours = data.get("hours")
            if not hours or float(hours) <= 0:
                return Response(
                    {"error": "hours must be greater than 0"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Parse and validate date
            entry_date_str = data.get("entry_date")
            if not entry_date_str:
                return Response(
                    {"error": "entry_date is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            entry_date = parse_date(entry_date_str)
            if not entry_date:
                return Response(
                    {"error": "entry_date must be in YYYY-MM-DD format"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Get job and staff with error handling
            try:
                job = Job.objects.get(id=job_id)
            except Job.DoesNotExist:
                return Response(
                    {"error": f"Job {job_id} not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            try:
                staff = Staff.objects.get(id=staff_id)
            except Staff.DoesNotExist:
                return Response(
                    {"error": f"Staff {staff_id} not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Extract other fields with defaults
            description = data.get("description", "")
            rate_multiplier = Decimal(str(data.get("rate_multiplier", 1.0)))
            is_billable = data.get("is_billable", True)

            # Get rates from staff and job
            wage_rate = staff.wage_rate
            charge_out_rate = job.charge_out_rate

            # Override rates if provided
            if data.get("wage_rate"):
                wage_rate = Decimal(str(data.get("wage_rate")))
            if data.get("charge_out_rate"):
                charge_out_rate = Decimal(str(data.get("charge_out_rate")))

            # Create CostLine using migration service
            with transaction.atomic():
                cost_line = TimesheetToCostLineService.create_cost_line_from_timesheet(
                    job_id=str(job_id),
                    staff_id=str(staff_id),
                    entry_date=entry_date,
                    hours=Decimal(str(hours)),
                    description=description,
                    wage_rate=wage_rate,
                    charge_out_rate=charge_out_rate,
                    rate_multiplier=rate_multiplier,
                    is_billable=is_billable,
                    ext_refs=data.get("ext_refs", {}),
                    meta=data.get("meta", {}),
                )

            # Serialize and return the created cost line
            serializer = CostLineSerializer(cost_line)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error creating timesheet entry: {e}")
            return Response(
                {"error": "Failed to create timesheet entry"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ModernTimesheetDayView(APIView):
    """
    Get timesheet entries for a specific day and staff

    GET /job/rest/timesheet/staff/<staff_id>/date/<date>/
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, staff_id, entry_date):
        """Get all cost lines for a staff member on a specific date"""
        try:
            # Parse date
            parsed_date = parse_date(entry_date)
            if not parsed_date:
                return Response(
                    {"error": "date must be in YYYY-MM-DD format"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Validate staff exists
            try:
                staff = Staff.objects.get(id=staff_id)
            except Staff.DoesNotExist:
                return Response(
                    {"error": f"Staff {staff_id} not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )  # Find all cost lines for this staff on this date
            cost_lines = (
                CostLine.objects.filter(
                    kind="time",
                    meta__staff_id=str(staff_id),
                    meta__entry_date=parsed_date.isoformat(),
                )
                .select_related("cost_set__job__client")
                .order_by("id")
            )

            # Serialize the cost lines using timesheet-specific serializer
            serializer = TimesheetCostLineSerializer(cost_lines, many=True)

            return Response(
                {
                    "staff_id": str(staff_id),
                    "staff_name": staff.get_display_full_name(),
                    "entry_date": entry_date,
                    "cost_lines": serializer.data,
                    "total_hours": sum(float(line.quantity) for line in cost_lines),
                    "total_cost": sum(line.total_cost for line in cost_lines),
                    "total_revenue": sum(line.total_rev for line in cost_lines),
                }
            )

        except Exception as e:
            logger.error(f"Error getting timesheet entries: {e}")
            return Response(
                {"error": "Failed to get timesheet entries"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ModernTimesheetJobView(APIView):
    """
    Get timesheet entries for a specific job

    GET /job/rest/timesheet/jobs/<job_id>/
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, job_id):
        """Get all timesheet cost lines for a job"""
        try:
            # Validate job exists
            job = get_object_or_404(Job, id=job_id)

            # Get the actual cost set
            cost_set = job.cost_sets.filter(kind="actual").order_by("-rev").first()

            if not cost_set:
                return Response(
                    {
                        "job_id": str(job_id),
                        "job_name": job.name,
                        "cost_lines": [],
                        "total_hours": 0,
                        "total_cost": 0,
                        "total_revenue": 0,
                    }
                )  # Get time cost lines (timesheet entries)
            timesheet_lines = cost_set.cost_lines.filter(
                kind="time", meta__created_from_timesheet=True
            ).order_by("meta__entry_date", "id")

            # Serialize the cost lines using timesheet-specific serializer
            serializer = TimesheetCostLineSerializer(timesheet_lines, many=True)

            return Response(
                {
                    "job_id": str(job_id),
                    "job_name": job.name,
                    "job_number": job.job_number,
                    "cost_lines": serializer.data,
                    "total_hours": sum(
                        float(line.quantity) for line in timesheet_lines
                    ),
                    "total_cost": sum(line.total_cost for line in timesheet_lines),
                    "total_revenue": sum(line.total_rev for line in timesheet_lines),
                }
            )

        except Exception as e:
            logger.error(f"Error getting job timesheet entries: {e}")
            return Response(
                {"error": "Failed to get job timesheet entries"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
