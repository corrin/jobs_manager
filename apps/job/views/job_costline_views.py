"""
CostLine REST Views

REST views for CostLine CRUD operations following clean code principles:
- SRP (Single Responsibility Principle)
- Early return and guard clauses
- Delegation to service layer
- Views as orchestrators only
"""

import logging

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.job.models import CostLine, CostSet, Job
from apps.job.serializers.costing_serializer import (
    CostLineCreateUpdateSerializer,
    CostLineSerializer,
)

logger = logging.getLogger(__name__)


class CostLineCreateView(APIView):
    """
    Create a new CostLine in the specified job's CostSet

    POST /job/rest/jobs/<job_id>/cost_sets/<kind>/cost_lines/
    POST /job/rest/jobs/<job_id>/cost_sets/actual/cost_lines/ (legacy)
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, job_id, kind="actual"):
        """Create a new cost line"""
        # Guard clause - validate job exists
        job = get_object_or_404(Job, id=job_id)

        # Validate kind parameter
        valid_kinds = ["estimate", "quote", "actual"]
        if kind not in valid_kinds:
            return Response(
                {"error": f"Invalid kind. Must be one of: {', '.join(valid_kinds)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                # Get or create CostSet for the specified kind
                cost_set = self._get_or_create_cost_set(job, kind)
                # Log the incoming data for debugging
                logger.info(f"Creating cost line with data: {request.data}")

                # Validate and create cost line
                serializer = CostLineCreateUpdateSerializer(data=request.data)
                if not serializer.is_valid():
                    logger.error(f"Cost line validation failed for job {job_id}:")
                    logger.error(f"Received data: {request.data}")
                    logger.error(f"Validation errors: {serializer.errors}")
                    return Response(
                        serializer.errors, status=status.HTTP_400_BAD_REQUEST
                    )

                # Create the cost line
                cost_line = serializer.save(cost_set=cost_set)

                # Update cost set summary
                self._update_cost_set_summary(cost_set)

                # Return created cost line
                response_serializer = CostLineSerializer(cost_line)
                return Response(
                    response_serializer.data, status=status.HTTP_201_CREATED
                )

        except Exception as e:
            logger.error(f"Error creating cost line for job {job_id}: {e}")
            return Response(
                {"error": "Failed to create cost line"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _get_or_create_cost_set(self, job: Job, kind: str) -> CostSet:
        """Get or create a CostSet for the job with the specified kind"""
        cost_set = job.cost_sets.filter(kind=kind).order_by("-rev").first()

        if not cost_set:
            # Create new cost set
            latest_rev = job.cost_sets.filter(kind=kind).count()
            cost_set = CostSet.objects.create(
                job=job,
                kind=kind,
                rev=latest_rev + 1,
                summary={"cost": 0, "rev": 0, "hours": 0},
            )
            logger.info(
                f"Created new {kind} CostSet rev {cost_set.rev} for job {job.id}"
            )

        return cost_set

    def _update_cost_set_summary(self, cost_set: CostSet) -> None:
        """Update cost set summary with aggregated data"""
        cost_lines = cost_set.cost_lines.all()

        total_cost = sum(line.total_cost for line in cost_lines)
        total_rev = sum(line.total_rev for line in cost_lines)
        total_hours = sum(
            float(line.quantity) for line in cost_lines if line.kind == "time"
        )

        cost_set.summary = {
            "cost": float(total_cost),
            "rev": float(total_rev),
            "hours": total_hours,
        }
        cost_set.save()


class CostLineUpdateView(APIView):
    """
    Update an existing CostLine

    PATCH /job/rest/cost_lines/<cost_line_id>/
    """

    permission_classes = [IsAuthenticated]

    def patch(self, request, cost_line_id):
        """Update a cost line"""
        # Guard clause - validate cost line exists
        cost_line = get_object_or_404(CostLine, id=cost_line_id)

        try:
            with transaction.atomic():
                # Validate and update cost line
                serializer = CostLineCreateUpdateSerializer(
                    cost_line, data=request.data, partial=True
                )

                if not serializer.is_valid():
                    return Response(
                        serializer.errors, status=status.HTTP_400_BAD_REQUEST
                    )

                # Save updated cost line
                updated_cost_line = serializer.save()

                # Update cost set summary
                self._update_cost_set_summary(updated_cost_line.cost_set)

                # Return updated cost line
                response_serializer = CostLineSerializer(updated_cost_line)
                return Response(response_serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error updating cost line {cost_line_id}: {e}")
            return Response(
                {"error": "Failed to update cost line"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _update_cost_set_summary(self, cost_set: CostSet) -> None:
        """Update cost set summary with aggregated data"""
        cost_lines = cost_set.cost_lines.all()

        total_cost = sum(line.total_cost for line in cost_lines)
        total_rev = sum(line.total_rev for line in cost_lines)
        total_hours = sum(
            float(line.quantity) for line in cost_lines if line.kind == "time"
        )

        cost_set.summary = {
            "cost": float(total_cost),
            "rev": float(total_rev),
            "hours": total_hours,
        }
        cost_set.save()


class CostLineDeleteView(APIView):
    """
    Delete an existing CostLine

    DELETE /job/rest/cost_lines/<cost_line_id>/
    """

    permission_classes = [IsAuthenticated]

    def delete(self, request, cost_line_id):
        """Delete a cost line"""
        # Guard clause - validate cost line exists
        cost_line = get_object_or_404(CostLine, id=cost_line_id)

        try:
            with transaction.atomic():
                cost_set = cost_line.cost_set

                # Delete the cost line
                cost_line.delete()
                logger.info(f"Deleted cost line {cost_line_id}")

                # Update cost set summary
                self._update_cost_set_summary(cost_set)

                return Response(status=status.HTTP_204_NO_CONTENT)

        except Exception as e:
            logger.error(f"Error deleting cost line {cost_line_id}: {e}")
            return Response(
                {"error": "Failed to delete cost line"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _update_cost_set_summary(self, cost_set: CostSet) -> None:
        """Update cost set summary with aggregated data"""
        cost_lines = cost_set.cost_lines.all()

        total_cost = sum(line.total_cost for line in cost_lines)
        total_rev = sum(line.total_rev for line in cost_lines)
        total_hours = sum(
            float(line.quantity) for line in cost_lines if line.kind == "time"
        )

        cost_set.summary = {
            "cost": float(total_cost),
            "rev": float(total_rev),
            "hours": total_hours,
        }
        cost_set.save()
