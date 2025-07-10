"""REST views for purchasing module."""

import logging
from decimal import Decimal

from django.core.cache import cache
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.job.models import Job
from apps.purchasing.models import PurchaseOrder, Stock
from apps.purchasing.serializers import (
    AllJobsResponseSerializer,
    DeliveryReceiptRequestSerializer,
    DeliveryReceiptResponseSerializer,
    PurchaseOrderAllocationsResponseSerializer,
    PurchaseOrderCreateResponseSerializer,
    PurchaseOrderCreateSerializer,
    PurchaseOrderDetailSerializer,
    PurchaseOrderListSerializer,
    PurchaseOrderUpdateResponseSerializer,
    PurchaseOrderUpdateSerializer,
    StockCreateResponseSerializer,
    StockCreateSerializer,
    StockListSerializer,
)
from apps.purchasing.services.delivery_receipt_service import process_delivery_receipt
from apps.purchasing.services.purchasing_rest_service import PurchasingRestService
from apps.purchasing.services.stock_service import consume_stock
from apps.workflow.api.xero.xero import get_xero_items

logger = logging.getLogger(__name__)


class AllJobsAPIView(APIView):
    """
    API endpoint to get all jobs with stock holding job flag.

    This endpoint is specifically for purchasing contexts like delivery receipt
    and stock allocation where we need all jobs but want to identify which one
    is the stock holding job.
    """

    serializer_class = AllJobsResponseSerializer

    def get(self, request):
        """Get all jobs with stock holding job flag."""
        try:
            # Get the stock holding job using the existing method
            stock_holding_job = Stock.get_stock_holding_job()

            # Get all jobs (both active and archived to be comprehensive)
            jobs = Job.objects.select_related("client").order_by("job_number")

            # Add stock holding flag to each job
            for job in jobs:
                job._is_stock_holding = job.id == stock_holding_job.id

            # Serialize the response
            response_data = {
                "success": True,
                "jobs": jobs,
                "stock_holding_job_id": str(stock_holding_job.id),
            }

            serializer = self.serializer_class(response_data)
            return Response(serializer.data)

        except Exception as e:
            logger.error(f"Error fetching all jobs: {e}")
            return Response(
                {"success": False, "error": "Failed to fetch jobs", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PurchasingJobsAPIView(APIView):
    """API endpoint to get jobs for purchasing contexts (PO lines, stock allocation, etc.)."""

    def get(self, request):
        """Get list of jobs suitable for purchasing operations."""
        try:
            # Get jobs that are active and can have costs allocated to them
            # Exclude jobs with status that shouldn't be available for purchasing
            excluded_statuses = ["rejected", "archived", "completed", "special"]
            jobs = (
                Job.objects.filter(
                    status__in=[
                        "quoting",
                        "accepted_quote",
                        "awaiting_materials",
                        "awaiting_staff",
                        "awaiting_site_availability",
                        "in_progress",
                        "on_hold",
                        "recently_completed",
                    ]
                )
                .exclude(status__in=excluded_statuses)
                .select_related("client")
                .prefetch_related("cost_sets")
                .order_by("job_number")
            )

            # Filter jobs that can accept cost allocations
            jobs_for_purchasing = []
            for job in jobs:
                # Jobs should be able to accept material/purchasing costs
                # Either they have cost sets or are in a state where we can create them
                if (
                    job.status
                    in [
                        "in_progress",
                        "on_hold",
                        "awaiting_materials",
                        "awaiting_staff",
                        "awaiting_site_availability",
                        "recently_completed",
                        "quoting",
                    ]
                    and job.latest_actual
                ):
                    jobs_for_purchasing.append(job)

            if not jobs_for_purchasing:
                return Response({"jobs": []})

            # Serialize jobs for purchasing context
            jobs_data = []
            for job in jobs_for_purchasing:
                actual_cost_set = job.get_latest("actual")
                jobs_data.append(
                    {
                        "id": str(job.id),
                        "job_number": job.job_number,
                        "name": job.name,
                        "client_name": job.client.name if job.client else "No Client",
                        "status": job.status,
                        "charge_out_rate": float(job.charge_out_rate or 0),
                        "cost_set_id": str(actual_cost_set.id)
                        if actual_cost_set
                        else None,
                        "job_display_name": f"{job.job_number} - {job.name}",
                    }
                )

            return Response(jobs_data)

        except Exception as e:
            logger.error(f"Error fetching jobs for purchasing: {e}")
            return Response(
                {"error": "Failed to fetch jobs", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class XeroItemList(APIView):
    """Return list of items from Xero."""

    def get(self, request):
        try:
            items = PurchasingRestService.list_xero_items()
            return Response(items)
        except Exception as e:
            logger.error("Error fetching Xero items: %s", e)
            return Response(
                {"error": "Failed to fetch Xero items"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PurchaseOrderListCreateRestView(APIView):
    """
    REST API view for listing and creating purchase orders.

    GET: Returns list of purchase orders with optional status filtering
    POST: Creates new purchase order from provided data
    """

    def get_serializer_class(self):
        """Return appropriate serializer class based on request method."""
        if self.request.method == "POST":
            return PurchaseOrderCreateSerializer
        return PurchaseOrderListSerializer

    def get(self, request):
        """Get list of purchase orders with optional status filtering."""
        status_filter = request.query_params.get("status", None)

        # Get data from service (returns list of dictionaries)
        data = PurchasingRestService.list_purchase_orders()

        if status_filter:
            # Support multiple status values separated by comma
            allowed_statuses = [s.strip() for s in status_filter.split(",")]
            data = [po for po in data if po["status"] in allowed_statuses]

        # Serialize the data from service using the serializer
        serializer = PurchaseOrderListSerializer(data, many=True)
        return Response(serializer.data)

    def post(self, request):
        """Create new purchase order."""
        serializer = PurchaseOrderCreateSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {"error": "Invalid input data", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Create PO using service
            po = PurchasingRestService.create_purchase_order(serializer.validated_data)

            # Return response
            response_data = {
                "id": str(po.id),
                "po_number": po.po_number,
            }
            response_serializer = PurchaseOrderCreateResponseSerializer(response_data)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error creating purchase order: {str(e)}")
            return Response(
                {"error": "Failed to create purchase order", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PurchaseOrderDetailRestView(APIView):
    """Returns a full PO (including lines)"""

    def get_serializer_class(self):
        """Return appropriate serializer class based on request method."""
        if self.request.method == "PATCH":
            return PurchaseOrderUpdateSerializer
        return PurchaseOrderDetailSerializer

    def get(self, request, pk):
        """Get purchase order details including lines."""
        # Allow fetching PO details regardless of status (including deleted)
        # to match the list endpoint behavior and allow viewing deleted POs
        queryset = (
            PurchaseOrder.objects.all()
            .select_related("supplier")
            .prefetch_related("po_lines")
        )
        po = get_object_or_404(queryset, id=pk)
        serializer = PurchaseOrderDetailSerializer(po)
        return Response(serializer.data)

    def patch(self, request, pk):
        """Update purchase order."""
        serializer = PurchaseOrderUpdateSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {"error": "Invalid input data", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Update PO using service
            po = PurchasingRestService.update_purchase_order(
                pk, serializer.validated_data
            )

            # Return response
            response_data = {
                "id": str(po.id),
                "status": po.status,
            }
            response_serializer = PurchaseOrderUpdateResponseSerializer(response_data)
            return Response(response_serializer.data)

        except Exception as e:
            logger.error(f"Error updating purchase order {pk}: {str(e)}")
            return Response(
                {"error": "Failed to update purchase order", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class DeliveryReceiptRestView(APIView):
    """
    REST API view for processing delivery receipts.

    POST: Processes delivery receipt for a purchase order with stock allocations
    """

    serializer_class = DeliveryReceiptRequestSerializer

    def post(self, request):
        try:
            # Validate input data
            serializer = self.serializer_class(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {"error": "Invalid input data", "details": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            validated_data = serializer.validated_data
            purchase_order_id = validated_data["purchase_order_id"]
            allocations = validated_data["allocations"]

            # Process the delivery receipt
            process_delivery_receipt(purchase_order_id, allocations)

            # Return success response
            response_data = {"success": True}
            response_serializer = DeliveryReceiptResponseSerializer(response_data)
            return Response(response_serializer.data)

        except Exception as e:
            logger.error(f"Error processing delivery receipt: {str(e)}")
            response_data = {"success": False, "error": str(e)}
            response_serializer = DeliveryReceiptResponseSerializer(response_data)
            return Response(
                response_serializer.data, status=status.HTTP_400_BAD_REQUEST
            )


class StockListRestView(APIView):
    """
    REST API view for listing and creating stock items.

    GET: Returns list of all stock items
    POST: Creates new stock item from provided data
    """

    def get_serializer_class(self):
        """Return appropriate serializer class based on request method."""
        if self.request.method == "POST":
            return StockCreateSerializer
        return StockListSerializer

    def get(self, request):
        """Get list of all active stock items."""
        # Get data from service (returns list of dictionaries)
        data = PurchasingRestService.list_stock()

        # Serialize the data from service using the serializer
        serializer = StockListSerializer(data, many=True)
        return Response(serializer.data)

    def post(self, request):
        """Create new stock item."""
        serializer = StockCreateSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {"error": "Invalid input data", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Create stock item using service
            item = PurchasingRestService.create_stock(serializer.validated_data)

            # Return response
            response_data = {"id": str(item.id)}
            response_serializer = StockCreateResponseSerializer(response_data)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except ValueError as exc:
            return Response(
                {"error": "Validation error", "details": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error(f"Error creating stock item: {str(e)}")
            return Response(
                {"error": "Failed to create stock item", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class StockDeactivateRestView(APIView):
    """
    REST API view for deactivating stock items.

    DELETE: Marks a stock item as inactive instead of deleting it
    """

    def delete(self, request, stock_id):
        item = get_object_or_404(Stock, id=stock_id)
        if item.is_active:
            item.is_active = False
            item.save()
            return Response({"success": True})
        return Response(
            {"error": "Item is already inactive"}, status=status.HTTP_400_BAD_REQUEST
        )


class StockConsumeRestView(APIView):
    """
    REST API view for consuming stock items for jobs.

    POST: Records stock consumption for a specific job, reducing available quantity
    """

    def post(self, request, stock_id):
        job_id = request.data.get("job_id")
        qty = request.data.get("quantity")
        if not all([job_id, qty]):
            return Response(
                {"error": "Missing data"}, status=status.HTTP_400_BAD_REQUEST
            )

        job = get_object_or_404(Job, id=job_id)
        item = get_object_or_404(Stock, id=stock_id)
        try:
            qty_dec = Decimal(str(qty))
        except Exception:
            return Response(
                {"error": "Invalid quantity"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            consume_stock(item, job, qty_dec, request.user)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"success": True})


class PurchaseOrderAllocationsAPIView(APIView):
    """
    API endpoint to get existing allocations for a purchase order.

    This helps show previous delivery receipt allocations when creating
    new delivery receipts for partially received orders.
    """

    serializer_class = PurchaseOrderAllocationsResponseSerializer

    def get(self, request, po_id):
        """Get existing allocations for a purchase order."""
        try:
            # Import here to avoid circular imports
            from django.db.models import CharField, F, Func, Value

            from apps.job.models import CostLine

            # Verify PO exists
            po = get_object_or_404(PurchaseOrder, id=po_id)
            logger.info(f"Looking for allocations for PO {po_id} ({po.po_number})")

            # Find all CostLines that reference this PO using JSON extraction
            cost_lines = (
                CostLine.objects.annotate(
                    po_id_from_refs=Func(
                        F("ext_refs"),
                        Value("$.purchase_order_id"),
                        function="JSON_UNQUOTE",
                        template="JSON_UNQUOTE(JSON_EXTRACT(%(expressions)s))",
                        output_field=CharField(),
                    )
                )
                .filter(po_id_from_refs=str(po_id))
                .select_related("cost_set__job")
            )

            # Find all Stock items that reference this PO
            stock_items = Stock.objects.filter(
                source="purchase_order",
                source_purchase_order_line__purchase_order_id=po_id,
            ).select_related("job", "source_purchase_order_line")

            logger.info(
                f"Found {cost_lines.count()} CostLines and {stock_items.count()} Stock items for PO {po_id}"
            )

            # Let's also debug what CostLines we have in total that might be related
            all_cost_lines_with_po_refs = CostLine.objects.filter(
                ext_refs__isnull=False
            ).exclude(ext_refs={})[
                :10
            ]  # Limit to first 10 for debugging

            logger.debug("Sample CostLines with ext_refs:")
            for cl in all_cost_lines_with_po_refs:
                logger.debug(f"  CostLine {cl.id}: ext_refs = {cl.ext_refs}")

            # Group allocations by PO line
            allocations_by_line = {}

            # Process CostLines (direct job allocations)
            for cost_line in cost_lines:
                # Extract purchase_order_line_id from ext_refs JSON field
                line_id = None
                if cost_line.ext_refs and isinstance(cost_line.ext_refs, dict):
                    line_id = cost_line.ext_refs.get("purchase_order_line_id")

                if line_id:
                    # Ensure line_id is always a string for consistency
                    line_id = str(line_id)
                    if line_id not in allocations_by_line:
                        allocations_by_line[line_id] = []

                    allocations_by_line[line_id].append(
                        {
                            "type": "job",
                            "job_id": str(cost_line.cost_set.job.id),
                            "job_name": cost_line.cost_set.job.name,
                            "quantity": float(cost_line.quantity),
                            "retail_rate": float(cost_line.meta.get("retail_rate", 0))
                            * 100
                            if cost_line.meta.get("retail_rate")
                            else 0,
                            "allocation_date": cost_line.created_at.isoformat()
                            if hasattr(cost_line, "created_at")
                            else None,
                            "description": cost_line.desc,
                        }
                    )
                    logger.debug(
                        f"Added CostLine allocation for line {line_id}: {cost_line.quantity} units to {cost_line.cost_set.job.name}"
                    )
                else:
                    logger.warning(
                        f"CostLine {cost_line.id} has no purchase_order_line_id in ext_refs: {cost_line.ext_refs}"
                    )

            # Process Stock items (stock allocations)
            for stock_item in stock_items:
                line_id = str(stock_item.source_purchase_order_line.id)
                if line_id not in allocations_by_line:
                    allocations_by_line[line_id] = []

                allocations_by_line[line_id].append(
                    {
                        "type": "stock",
                        "job_id": str(stock_item.job.id),
                        "job_name": "Stock"
                        if stock_item.job.name == "Worker Admin"
                        else stock_item.job.name,
                        "quantity": float(stock_item.quantity),
                        "retail_rate": 0,  # Stock items don't have retail rate
                        "allocation_date": stock_item.date.isoformat(),
                        "description": stock_item.description,
                        "stock_location": stock_item.location or "Not specified",
                    }
                )
                logger.debug(
                    f"Added Stock allocation for line {line_id}: {stock_item.quantity} units to stock"
                )

            logger.info(
                f"Total allocations found: {sum(len(allocs) for allocs in allocations_by_line.values())} across {len(allocations_by_line)} lines"
            )

            # Serialize the response
            response_data = {"po_id": str(po_id), "allocations": allocations_by_line}

            serializer = self.serializer_class(response_data)
            return Response(serializer.data)

        except Exception as e:
            logger.error(f"Error fetching allocations for PO {po_id}: {e}")
            return Response(
                {"error": f"Failed to fetch allocations: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
