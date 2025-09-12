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
from django.db.models import F
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.job.models import CostLine, CostSet, Job
from apps.job.serializers.costing_serializer import (
    CostLineCreateUpdateSerializer,
    CostLineErrorResponseSerializer,
    CostLineSerializer,
)
from apps.purchasing.models import Stock

logger = logging.getLogger(__name__)


class CostLineCreateView(APIView):
    """
    Create a new CostLine in the specified job's CostSet

    POST /job/rest/jobs/<job_id>/cost_sets/<kind>/cost_lines/
    POST /job/rest/jobs/<job_id>/cost_sets/actual/cost_lines/ (legacy)
    """

    permission_classes = [IsAuthenticated]
    serializer_class = CostLineSerializer

    def get_serializer_class(self):
        """Return the appropriate serializer class based on the request method"""
        if self.request.method == "POST":
            return CostLineCreateUpdateSerializer
        return CostLineSerializer

    def post(self, request, job_id, kind="actual"):
        """Create a new cost line"""
        # Guard clause - validate job exists
        job = get_object_or_404(Job, id=job_id)

        # Validate kind parameter
        valid_kinds = ["estimate", "quote", "actual"]
        if kind not in valid_kinds:
            error_response = {
                "error": f"Invalid kind. Must be one of: {', '.join(valid_kinds)}"
            }
            error_serializer = CostLineErrorResponseSerializer(error_response)
            return Response(error_serializer.data, status=status.HTTP_400_BAD_REQUEST)

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

                # Return created cost line
                response_serializer = CostLineSerializer(cost_line)
                return Response(
                    response_serializer.data, status=status.HTTP_201_CREATED
                )

        except Exception as e:
            logger.error(f"Error creating cost line for job {job_id}: {e}")
            error_response = {"error": "Failed to create cost line"}
            error_serializer = CostLineErrorResponseSerializer(error_response)
            return Response(
                error_serializer.data, status=status.HTTP_500_INTERNAL_SERVER_ERROR
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


class CostLineUpdateView(APIView):
    """
    Update an existing CostLine

    PATCH /job/rest/cost_lines/<cost_line_id>/
    """

    permission_classes = [IsAuthenticated]
    serializer_class = CostLineSerializer

    def get_serializer_class(self):
        """Return the appropriate serializer class based on the request method"""
        if self.request.method == "PATCH":
            return CostLineCreateUpdateSerializer
        return CostLineSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="cost_line_id",
                type=str,
                location=OpenApiParameter.PATH,
                description="ID of the CostLine to update",
            )
        ]
    )
    def patch(self, request, cost_line_id):
        """
        Update a cost line
        Dynamically infers the stock adjustment based on quantity change
        """
        cost_line = get_object_or_404(CostLine, id=cost_line_id)

        try:
            with transaction.atomic():
                old_qty = cost_line.quantity or 0

                serializer = CostLineCreateUpdateSerializer(
                    cost_line, data=request.data, partial=True
                )
                if not serializer.is_valid():
                    return Response(
                        serializer.errors, status=status.HTTP_400_BAD_REQUEST
                    )

                updated_cost_line = serializer.save()

                stock_id = (updated_cost_line.ext_refs or {}).get("stock_id")

                new_qty = updated_cost_line.quantity or 0
                diff = new_qty - old_qty

                if stock_id and diff:
                    self._update_stock(stock_id, diff)

                response_serializer = CostLineSerializer(updated_cost_line)
                return Response(response_serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error updating cost line {cost_line_id}: {e}")
            error_response = {"error": "Failed to update cost line"}
            error_serializer = CostLineErrorResponseSerializer(error_response)
            return Response(
                error_serializer.data, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _update_stock(self, stock_id: str, diff) -> None:
        """Atomic decrement/increment via F() to avoid races"""
        with transaction.atomic():
            Stock.objects.filter(pk=stock_id).update(quantity=F("quantity") - diff)


class CostLineDeleteView(APIView):
    """
    Delete an existing CostLine

    DELETE /job/rest/cost_lines/<cost_line_id>/
    """

    permission_classes = [IsAuthenticated]
    serializer_class = CostLineErrorResponseSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="cost_line_id",
                type=str,
                location=OpenApiParameter.PATH,
                description="ID of the CostLine to delete",
            )
        ],
        responses={
            204: None,
            400: CostLineErrorResponseSerializer,
            500: CostLineErrorResponseSerializer,
        },
        description="Delete an existing CostLine by ID",
    )
    def delete(self, request, cost_line_id):
        """Delete a cost line"""
        # Guard clause - validate cost line exists
        cost_line = get_object_or_404(CostLine, id=cost_line_id)

        try:
            with transaction.atomic():
                stock_id = (cost_line.ext_refs or {}).get("stock_id")
                if stock_id and cost_line.quantity:
                    # quantity = quantity + cost_line.quantity
                    Stock.objects.filter(pk=stock_id).update(
                        quantity=F("quantity") + cost_line.quantity
                    )

                cost_line.delete()
                logger.info(f"Deleted cost line {cost_line_id}")
                return Response(status=status.HTTP_204_NO_CONTENT)

        except Exception as e:
            logger.error(f"Error deleting cost line {cost_line_id}: {e}")
            error_response = {"error": "Failed to delete cost line"}
            error_serializer = CostLineErrorResponseSerializer(error_response)
            return Response(
                error_serializer.data, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
