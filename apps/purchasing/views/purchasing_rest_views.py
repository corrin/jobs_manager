"""REST views for purchasing module."""

import logging
import traceback
from decimal import Decimal, InvalidOperation

from django.db.models import OuterRef, Subquery
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.job.models import Job
from apps.purchasing.models import PurchaseOrder, Stock
from apps.purchasing.serializers import (
    AllJobsResponseSerializer,
    AllocationDeleteRequestSerializer,
    AllocationDeleteResponseSerializer,
    AllocationDetailsResponseSerializer,
    DeliveryReceiptRequestSerializer,
    DeliveryReceiptResponseSerializer,
    PurchaseOrderAllocationsResponseSerializer,
    PurchaseOrderCreateResponseSerializer,
    PurchaseOrderCreateSerializer,
    PurchaseOrderDetailSerializer,
    PurchaseOrderListSerializer,
    PurchaseOrderUpdateResponseSerializer,
    PurchaseOrderUpdateSerializer,
    PurchasingJobsResponseSerializer,
    StockConsumeRequestSerializer,
    StockConsumeResponseSerializer,
    StockCreateResponseSerializer,
    StockCreateSerializer,
    StockDeactivateResponseSerializer,
    StockListSerializer,
    SupplierPriceStatusResponseSerializer,
    XeroItemListResponseSerializer,
)
from apps.purchasing.services.allocation_service import (
    AllocationDeletionError,
    AllocationService,
)
from apps.purchasing.services.delivery_receipt_service import process_delivery_receipt
from apps.purchasing.services.purchasing_rest_service import PurchasingRestService
from apps.purchasing.services.stock_service import consume_stock

logger = logging.getLogger(__name__)


class SupplierPriceStatusAPIView(APIView):
    """Return latest price upload status per supplier.

    Minimal-impact: read-only query over existing Client and SupplierPriceList
    models. No migrations required.
    """

    serializer_class = SupplierPriceStatusResponseSerializer

    @extend_schema(
        operation_id="getSupplierPriceStatus",
        responses=SupplierPriceStatusResponseSerializer,
    )
    def get(self, request):
        try:
            from apps.client.models import Client
            from apps.quoting.models import SupplierPriceList

            # Subquery to get the latest upload per supplier
            latest_pl = SupplierPriceList.objects.filter(
                supplier_id=OuterRef("pk")
            ).order_by("-uploaded_at")

            suppliers = (
                Client.objects.filter(
                    id__in=SupplierPriceList.objects.values("supplier_id").distinct()
                )
                .annotate(
                    last_uploaded_at=Subquery(latest_pl.values("uploaded_at")[:1]),
                    last_file_name=Subquery(latest_pl.values("file_name")[:1]),
                )
                .order_by("name")
            )

            # Build response rows, including counts and change estimate (no migrations)
            items = []
            from apps.quoting.models import SupplierProduct

            for s in suppliers:
                # Find latest and previous price lists for this supplier
                pls = (
                    SupplierPriceList.objects.filter(supplier_id=s.id)
                    .order_by("-uploaded_at")
                    .values_list("id", "file_name", "uploaded_at")
                )
                total_products = None
                changes_last_update = None
                if pls:
                    latest_id, latest_file, latest_dt = pls[0]
                    # Count all supplier products linked to this supplier (across price lists)
                    total_products = SupplierProduct.objects.filter(
                        supplier_id=s.id
                    ).count()
                    if len(pls) > 1:
                        prev_id, _, _ = pls[1]
                        latest_keys = set(
                            SupplierProduct.objects.filter(
                                price_list_id=latest_id
                            ).values_list("item_no", "variant_id")
                        )
                        prev_keys = set(
                            SupplierProduct.objects.filter(
                                price_list_id=prev_id
                            ).values_list("item_no", "variant_id")
                        )
                        additions = len(latest_keys - prev_keys)
                        removals = len(prev_keys - latest_keys)
                        changes_last_update = additions + removals

                items.append(
                    {
                        "supplier_id": s.id,
                        "supplier_name": s.name,
                        "last_uploaded_at": s.last_uploaded_at,
                        "file_name": s.last_file_name,
                        "total_products": total_products,
                        "changes_last_update": changes_last_update,
                    }
                )

            resp = {"items": items, "total_count": len(items)}
            serializer = self.serializer_class(resp)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"Error computing supplier price status: {e}")
            return Response(
                {"error": "Failed to fetch supplier price status"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


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

    serializer_class = PurchasingJobsResponseSerializer

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
                        "cost_set_id": (
                            str(actual_cost_set.id) if actual_cost_set else None
                        ),
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

    serializer_class = XeroItemListResponseSerializer

    def get(self, request):
        try:
            items = PurchasingRestService.list_xero_items()
            return Response({"items": items, "total_count": len(items)})
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

    @extend_schema(
        operation_id="listPurchaseOrders",
        responses={
            status.HTTP_200_OK: PurchaseOrderListSerializer(many=True),
            status.HTTP_400_BAD_REQUEST: "Invalid input data",
        },
    )
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

    @extend_schema(operation_id="retrievePurchaseOrder")
    def get(self, request, id):
        """Get purchase order details including lines."""
        # Allow fetching PO details regardless of status (including deleted)
        # to match the list endpoint behavior and allow viewing deleted POs
        queryset = (
            PurchaseOrder.objects.all()
            .select_related("supplier")
            .prefetch_related("po_lines")
        )
        po = get_object_or_404(queryset, id=id)
        serializer = PurchaseOrderDetailSerializer(po)
        return Response(serializer.data)

    def patch(self, request, id):
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
                id, serializer.validated_data
            )

            # Return response
            response_data = {
                "id": str(po.id),
                "status": po.status,
            }
            response_serializer = PurchaseOrderUpdateResponseSerializer(response_data)
            return Response(response_serializer.data)

        except Exception as e:
            logger.error(f"Error updating purchase order {id}: {str(e)}")
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

    @extend_schema(
        responses={
            status.HTTP_200_OK: DeliveryReceiptResponseSerializer,
            status.HTTP_400_BAD_REQUEST: DeliveryReceiptResponseSerializer,
        }
    )
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


@method_decorator(
    cache_page(
        10
    ),  # Short cache to de-duplicate immediate double fetches from jobs page
    name="dispatch",
)
class StockListRestView(APIView):
    """
    REST API view for listing and creating stock items.

    GET: Returns list of all stock items
    POST: Creates new stock item from provided data
    """

    # Why cached:
    # - The jobs page triggers two back-to-back GETs to this endpoint on load.
    # - Caching for 10s removes redundant work and reduces perceived wait without changing frontend.
    # - Safe to revert by removing the cache_page decorator if behavior changes.

    def get_serializer_class(self):
        """Return appropriate serializer class based on request method."""
        if self.request.method == "POST":
            return StockCreateSerializer
        return StockListSerializer

    def get(self, request):
        """Get list of all active stock items."""
        # Get data from service (returns list of dictionaries)
        items = PurchasingRestService.list_stock()

        payload = {
            "items": items,
            "total_count": len(items),
        }

        # Serialize the data from service using the serializer
        serializer = StockListSerializer(payload)
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

    serializer_class = StockDeactivateResponseSerializer

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

    serializer_class = StockConsumeResponseSerializer

    def get_serializer_class(self):
        """Return the appropriate serializer class based on the request method"""
        if self.request.method == "POST":
            return StockConsumeRequestSerializer
        return StockConsumeResponseSerializer

    @extend_schema(
        request=StockConsumeRequestSerializer,
        responses=StockConsumeResponseSerializer,
        operation_id="consumeStock",
        description="Consume stock for a job, reducing available quantity.",
    )
    def post(self, request, stock_id):
        # Use serializer for proper validation
        serializer = StockConsumeRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Invalid input data", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        job_id = serializer.validated_data["job_id"]
        qty_dec = serializer.validated_data["quantity"]

        job = get_object_or_404(Job, id=job_id)
        item = get_object_or_404(Stock, id=stock_id)

        # Validating because unit cost and revenue are optional in consumption
        # (But stock alocation in JobActualTab might override default values for cost and revenue)
        unit_cost = request.data.get("unit_cost", None)
        unit_rev = request.data.get("unit_rev", None)
        cost_dec = None
        revenue_dec = None

        try:
            if unit_cost is not None:
                cost_dec = Decimal(str(unit_cost))
            if unit_rev is not None:
                revenue_dec = Decimal(str(unit_rev))
        except (InvalidOperation, TypeError):
            return Response(
                {
                    "error": "Invalid state detected: unit cost or unit revenue are not valid decimals"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            if cost_dec and revenue_dec:
                line = consume_stock(
                    item, job, qty_dec, request.user, cost_dec, revenue_dec
                )
            else:
                line = consume_stock(item, job, qty_dec, request.user)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        payload = {
            "success": True,
            "message": "Stock consumed successfully",
            "remaining_quantity": item.quantity - qty_dec,
            "line": line,
        }
        return Response(
            StockConsumeResponseSerializer(payload).data, status=status.HTTP_200_OK
        )


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
                            "retail_rate": (
                                float(cost_line.meta.get("retail_rate", 0)) * 100
                                if cost_line.meta.get("retail_rate")
                                else 0
                            ),
                            "allocation_date": (
                                cost_line.created_at.isoformat()
                                if hasattr(cost_line, "created_at")
                                else None
                            ),
                            "description": cost_line.desc,
                            "allocation_id": str(cost_line.id),
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
                        "job_name": (
                            "Stock"
                            if stock_item.job.name == "Worker Admin"
                            else stock_item.job.name
                        ),
                        "quantity": float(stock_item.quantity),
                        "retail_rate": (
                            float(stock_item.retail_rate * 100)
                            if stock_item.retail_rate
                            else 0
                        ),
                        "allocation_date": stock_item.date.isoformat(),
                        "description": stock_item.description,
                        "stock_location": stock_item.location or "Not specified",
                        "metal_type": stock_item.metal_type or "unspecified",
                        "alloy": stock_item.alloy or "",
                        "specifics": stock_item.specifics or "",
                        "allocation_id": str(stock_item.id),
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


class AllocationDeleteAPIView(APIView):
    """
    API endpoint to delete specific allocations from a purchase order.

    DELETE: Deletes a Stock item or CostLine allocation created from delivery receipt
    """

    serializer_class = AllocationDeleteResponseSerializer

    @extend_schema(
        request=AllocationDeleteRequestSerializer,
        responses={
            status.HTTP_200_OK: AllocationDeleteResponseSerializer,
            status.HTTP_400_BAD_REQUEST: AllocationDeleteResponseSerializer,
        },
        operation_id="deleteAllocation",
        description="Delete a specific allocation (Stock item or CostLine) from a purchase order line.",
    )
    def post(self, request, po_id, line_id):
        """Delete a specific allocation from a purchase order line."""
        try:
            # Validate input data
            serializer = AllocationDeleteRequestSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {
                        "success": False,
                        "message": "Invalid input data",
                        "details": serializer.errors,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            validated_data = serializer.validated_data
            allocation_type = validated_data["allocation_type"]
            allocation_id = str(validated_data["allocation_id"])

            # Delete the allocation using the service
            result = AllocationService.delete_allocation(
                po_id=str(po_id),
                line_id=line_id,
                allocation_type=allocation_type,
                allocation_id=allocation_id,
            )

            # Return success response
            response_serializer = self.serializer_class(result)
            return Response(response_serializer.data, status=status.HTTP_200_OK)

        except AllocationDeletionError as e:
            logger.error(f"Allocation deletion error: {str(e)}")
            response_data = {"success": False, "message": str(e)}
            response_serializer = self.serializer_class(response_data)
            return Response(
                response_serializer.data, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            traceback.print_exc()
            logger.error(f"Unexpected error deleting allocation: {str(e)}")
            response_data = {
                "success": False,
                "message": f"An unexpected error occurred: {str(e)}",
            }
            response_serializer = self.serializer_class(response_data)
            return Response(
                response_serializer.data, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AllocationDetailsAPIView(APIView):
    """
    API endpoint to get details about a specific allocation before deletion.

    GET: Returns details about a Stock item or CostLine allocation
    """

    serializer_class = AllocationDetailsResponseSerializer

    @extend_schema(
        responses={
            status.HTTP_200_OK: AllocationDetailsResponseSerializer,
            status.HTTP_404_NOT_FOUND: "Allocation not found",
        },
        operation_id="getAllocationDetails",
        description="Get details about a specific allocation before deletion.",
    )
    def get(self, request, po_id, allocation_type, allocation_id):
        """Get details about a specific allocation."""
        try:
            # Get allocation details using the service
            details = AllocationService.get_allocation_details(
                po_id=po_id,
                allocation_type=allocation_type,
                allocation_id=allocation_id,
            )

            # Return details
            response_serializer = self.serializer_class(details)
            return Response(response_serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error getting allocation details: {str(e)}")
            return Response(
                {"error": f"Failed to get allocation details: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
