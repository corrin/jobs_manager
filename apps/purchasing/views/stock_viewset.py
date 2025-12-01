"""
Stock ViewSet

ViewSet for Stock CRUD operations using DRF's ModelViewSet.
Provides list, create, retrieve, update, partial_update, and destroy actions.
"""

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.job.models import Job
from apps.purchasing.models import Stock
from apps.purchasing.serializers import (
    StockConsumeRequestSerializer,
    StockConsumeResponseSerializer,
    StockItemSerializer,
)
from apps.purchasing.services.stock_service import consume_stock


class StockViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Stock CRUD operations.

    Endpoints:
    - GET    /purchasing/rest/stock/              - list all active stock
    - POST   /purchasing/rest/stock/              - create stock item
    - GET    /purchasing/rest/stock/<id>/         - retrieve stock item
    - PUT    /purchasing/rest/stock/<id>/         - full update
    - PATCH  /purchasing/rest/stock/<id>/         - partial update
    - DELETE /purchasing/rest/stock/<id>/         - soft delete (sets is_active=False)

    Custom Actions:
    - POST   /purchasing/rest/stock/<id>/consume/ - consume stock for a job
    """

    queryset = Stock.objects.filter(is_active=True)
    serializer_class = StockItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Filter to only active stock items.
        """
        return Stock.objects.filter(is_active=True).order_by("-date")

    def perform_destroy(self, instance):
        """
        Soft delete - set is_active=False instead of actually deleting.
        """
        instance.is_active = False
        instance.save(update_fields=["is_active"])

    @extend_schema(
        request=StockConsumeRequestSerializer,
        responses=StockConsumeResponseSerializer,
        operation_id="consumeStock",
        description="Consume stock for a job, reducing available quantity.",
    )
    @action(detail=True, methods=["post"])
    def consume(self, request, pk=None):
        """
        Consume stock for a job, reducing available quantity.
        """
        stock_item = self.get_object()

        serializer = StockConsumeRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Invalid input data", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        job_id = serializer.validated_data["job_id"]
        qty_dec = serializer.validated_data["quantity"]
        unit_cost = serializer.validated_data.get("unit_cost")
        unit_rev = serializer.validated_data.get("unit_rev")

        # Get the job object
        job = get_object_or_404(Job, id=job_id)

        try:
            line = consume_stock(
                stock_item,
                job,
                qty_dec,
                request.user,
                unit_cost=unit_cost,
                unit_rev=unit_rev,
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        payload = {
            "success": True,
            "message": "Stock consumed successfully",
            "remaining_quantity": stock_item.quantity - qty_dec,
            "line": line,
        }
        return Response(
            StockConsumeResponseSerializer(payload).data, status=status.HTTP_200_OK
        )
