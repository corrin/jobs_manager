import logging
from decimal import Decimal
from typing import Dict

from django.db import models, transaction
from django.db.models import F, Func, Value

from apps.job.models import CostLine
from apps.purchasing.models import PurchaseOrder, PurchaseOrderLine, Stock
from apps.workflow.services.error_persistence import persist_app_error

logger = logging.getLogger(__name__)


class AllocationDeletionError(ValueError):
    """Custom exception for allocation deletion errors."""


class AllocationService:
    """Service for managing delivery receipt allocations."""

    @staticmethod
    def delete_allocation(
        po_id: str, line_id: str, allocation_type: str, allocation_id: str, user=None
    ) -> Dict[str, any]:
        """
        Delete a specific allocation (Stock item or CostLine) created from a delivery receipt.

        Args:
            po_id: Purchase Order ID
            line_id: Purchase Order Line ID
            allocation_type: Type of allocation ('stock' or 'job')
            allocation_id: ID of the Stock item or CostLine to delete
            user: User performing the deletion (for audit purposes)

        Returns:
            Dict with success status and details

        Raises:
            AllocationDeletionError: If deletion fails validation
            Exception: For other unexpected errors
        """
        logger.info(
            f"Starting allocation deletion - PO: {po_id}, Line: {line_id}, "
            f"Type: {allocation_type}, ID: {allocation_id}"
        )

        try:
            with transaction.atomic():
                # Validate PO exists first
                try:
                    po = PurchaseOrder.objects.get(id=po_id)
                    logger.debug(f"Found PO {po.po_number}")
                except PurchaseOrder.DoesNotExist:
                    raise AllocationDeletionError(f"Purchase Order {po_id} not found")

                # Find the PO line based on the allocation type and ID
                po_line = None
                if allocation_type == "stock":
                    try:
                        stock_item = Stock.objects.select_related(
                            "source_purchase_order_line"
                        ).get(
                            id=allocation_id,
                            source="purchase_order",
                            source_purchase_order_line__purchase_order=po,
                        )
                        po_line = stock_item.source_purchase_order_line
                        logger.debug(
                            f"Found PO line {po_line.description} via stock allocation"
                        )
                    except Stock.DoesNotExist:
                        raise AllocationDeletionError(
                            f"Stock allocation {allocation_id} not found or not from PO {po_id}"
                        )
                elif allocation_type == "job":
                    try:
                        cost_line = (
                            CostLine.objects.annotate(
                                po_id_from_refs=Func(
                                    F("ext_refs"),
                                    Value("$.purchase_order_id"),
                                    function="JSON_UNQUOTE",
                                    template="JSON_UNQUOTE(JSON_EXTRACT(%(expressions)s))",
                                    output_field=models.CharField(),
                                )
                            )
                            .filter(po_id_from_refs=str(po_id), id=allocation_id)
                            .select_related("cost_set__job")
                        ).first()
                        # Get the PO line ID from ext_refs
                        po_line_id = cost_line.ext_refs.get("purchase_order_line_id")
                        if not po_line_id:
                            raise AllocationDeletionError(
                                f"Cost line {allocation_id} does not have purchase_order_line_id in ext_refs"
                            )
                        po_line = PurchaseOrderLine.objects.get(
                            id=po_line_id, purchase_order=po
                        )
                        logger.debug(
                            f"Found PO line {po_line.description} via job allocation"
                        )
                    except CostLine.DoesNotExist:
                        raise AllocationDeletionError(
                            f"Job allocation {allocation_id} not found or not from PO {po_id}"
                        )
                    except PurchaseOrderLine.DoesNotExist:
                        raise AllocationDeletionError(
                            f"Purchase Order Line referenced by allocation {allocation_id} not found"
                        )
                else:
                    raise AllocationDeletionError(
                        f"Invalid allocation type: {allocation_type}. Must be 'stock' or 'job'"
                    )

                # Now delete the allocation
                if allocation_type == "stock":
                    return AllocationService._delete_stock_allocation(
                        po, po_line, allocation_id, user
                    )
                elif allocation_type == "job":
                    return AllocationService._delete_job_allocation(
                        po, po_line, allocation_id, user
                    )

        except AllocationDeletionError as e:
            logger.error(f"Allocation deletion validation error: {e}")
            persist_app_error(
                e,
                additional_context={
                    "po_id": str(po_id),
                    "line_id": str(line_id),
                    "allocation_type": str(allocation_type),
                    "allocation_id": str(allocation_id),
                },
            )
            raise
        except Exception as e:
            logger.error(f"Unexpected error during allocation deletion: {e}")
            persist_app_error(
                e,
                additional_context={
                    "po_id": str(po_id),
                    "line_id": str(line_id),
                    "allocation_type": str(allocation_type),
                    "allocation_id": str(allocation_id),
                },
            )
            raise

    @staticmethod
    def _delete_stock_allocation(
        po: PurchaseOrder, po_line: PurchaseOrderLine, stock_id: str, user=None
    ) -> Dict[str, any]:
        """Delete a stock allocation."""
        # Get the stock item (already validated in main method)
        stock_item = Stock.objects.get(id=stock_id)

        logger.debug(
            f"Found stock item: {stock_item.description}, qty: {stock_item.quantity}"
        )

        # Check if stock has been consumed by checking if any CostLines reference this stock item
        consuming_cost_lines = CostLine.objects.filter(
            ext_refs__stock_id=str(stock_item.id)
        )

        if consuming_cost_lines.exists():
            raise AllocationDeletionError(
                f"Cannot delete stock allocation - stock has been consumed by "
                f"{consuming_cost_lines.count()} job(s)"
            )

        # Store details for response
        deleted_quantity = stock_item.quantity
        description = stock_item.description

        # Update the PO line received quantity
        po_line.received_quantity -= deleted_quantity
        if po_line.received_quantity < 0:
            po_line.received_quantity = Decimal("0")
        po_line.save(update_fields=["received_quantity"])

        # Delete the stock item
        stock_item.delete()

        logger.info(
            f"Deleted stock allocation: {description}, qty: {deleted_quantity}, "
            f"updated PO line received qty to: {po_line.received_quantity}"
        )

        # Update PO status if needed
        AllocationService._update_po_status(po)

        return {
            "success": True,
            "message": "Stock allocation deleted successfully",
            "deleted_quantity": float(deleted_quantity),
            "description": description,
            "updated_received_quantity": float(po_line.received_quantity),
        }

    @staticmethod
    def _delete_job_allocation(
        po: PurchaseOrder, po_line: PurchaseOrderLine, cost_line_id: str, user=None
    ) -> Dict[str, any]:
        """Delete a job allocation (CostLine)."""
        # Get the cost line (already validated in main method)
        cost_line = CostLine.objects.select_related("cost_set__job").get(
            id=cost_line_id
        )

        logger.debug(
            f"Found cost line: {cost_line.desc}, qty: {cost_line.quantity}, "
            f"job: {cost_line.cost_set.job.name}"
        )

        # Store details for response
        deleted_quantity = cost_line.quantity
        description = cost_line.desc
        job_name = cost_line.cost_set.job.name

        # Update the PO line received quantity
        po_line.received_quantity -= deleted_quantity
        if po_line.received_quantity < 0:
            po_line.received_quantity = Decimal("0")
        po_line.save(update_fields=["received_quantity"])

        # Delete the cost line
        cost_line.delete()

        logger.info(
            f"Deleted job allocation: {description}, qty: {deleted_quantity}, "
            f"from job: {job_name}, updated PO line received qty to: {po_line.received_quantity}"
        )

        # Update PO status if needed
        AllocationService._update_po_status(po)

        return {
            "success": True,
            "message": "Job allocation deleted successfully",
            "deleted_quantity": float(deleted_quantity),
            "description": description,
            "job_name": job_name,
            "updated_received_quantity": float(po_line.received_quantity),
        }

    @staticmethod
    def _update_po_status(po: PurchaseOrder) -> None:
        """Update PO status based on current received quantities."""
        # Re-fetch all lines to get updated quantities
        all_po_lines = po.po_lines.all()
        current_total_ordered = sum(line.quantity for line in all_po_lines)
        current_total_received = sum(line.received_quantity for line in all_po_lines)

        logger.debug(
            f"Updating PO status - Total Received: {current_total_received}, "
            f"Total Ordered: {current_total_ordered}"
        )

        new_status = po.status  # Default to current

        if current_total_received <= 0:
            if po.status != "deleted":  # Avoid changing deleted status
                new_status = "submitted"
        elif current_total_received < current_total_ordered:
            new_status = "partially_received"
        else:  # received >= ordered
            new_status = "fully_received"

        if new_status != po.status:
            po.status = new_status
            po.save(update_fields=["status"])
            logger.debug(f"Updated PO {po.po_number} status to {po.status}")
        else:
            logger.debug(f"PO {po.po_number} status remains {po.status}")

    @staticmethod
    def get_allocation_details(
        po_id: str, allocation_type: str, allocation_id: str
    ) -> Dict[str, any]:
        """
        Get details about a specific allocation before deletion.

        Args:
            po_id: Purchase Order ID
            allocation_type: Type of allocation ('stock' or 'job')
            allocation_id: ID of the Stock item or CostLine

        Returns:
            Dict with allocation details
        """
        try:
            # Validate PO exists
            try:
                po = PurchaseOrder.objects.get(id=po_id)
            except PurchaseOrder.DoesNotExist:
                raise AllocationDeletionError(f"Purchase Order {po_id} not found")

            if allocation_type == "stock":
                try:
                    stock_item = Stock.objects.get(
                        id=allocation_id,
                        source="purchase_order",
                        source_purchase_order_line__purchase_order=po,
                    )
                except Stock.DoesNotExist:
                    raise AllocationDeletionError(
                        f"Stock item {allocation_id} not found or not from PO {po_id}"
                    )

                # Check if consumed
                consuming_cost_lines = CostLine.objects.filter(
                    ext_refs__stock_id=str(stock_item.id)
                )

                return {
                    "type": "stock",
                    "id": str(stock_item.id),
                    "description": stock_item.description,
                    "quantity": float(stock_item.quantity),
                    "job_name": stock_item.job.name if stock_item.job else "No Job",
                    "can_delete": not consuming_cost_lines.exists(),
                    "consumed_by_jobs": consuming_cost_lines.count(),
                    "location": stock_item.location or "Not specified",
                }

            elif allocation_type == "job":
                try:
                    cost_line = CostLine.objects.get(
                        id=allocation_id, ext_refs__purchase_order_id=str(po.id)
                    )
                except CostLine.DoesNotExist:
                    raise AllocationDeletionError(
                        f"Cost line {allocation_id} not found or not from PO {po_id}"
                    )

                return {
                    "type": "job",
                    "id": str(cost_line.id),
                    "description": cost_line.desc,
                    "quantity": float(cost_line.quantity),
                    "job_name": cost_line.cost_set.job.name,
                    "can_delete": True,  # Job allocations can generally be deleted
                    "unit_cost": float(cost_line.unit_cost),
                    "unit_revenue": float(cost_line.unit_rev),
                }
            else:
                raise AllocationDeletionError(
                    f"Invalid allocation type: {allocation_type}"
                )

        except Exception as e:
            logger.error(f"Error getting allocation details: {e}")
            persist_app_error(
                e,
                additional_context={
                    "po_id": str(po_id),
                    "allocation_type": str(allocation_type),
                    "allocation_id": str(allocation_id),
                },
            )
            raise
