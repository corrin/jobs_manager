from decimal import Decimal
from django.db import transaction
from django.utils import timezone
import logging

from workflow.models.purchase import PurchaseOrder, PurchaseOrderLine
from workflow.models.stock import Stock
from workflow.models.job import JobPricing

logger = logging.getLogger(__name__)

def process_delivery_receipt(purchase_order_id: str, received_quantities: dict) -> bool:
    """
    Process a delivery receipt for a purchase order.
    
    This function:
    1. Updates the PO line items with received quantities
    2. Creates stock entries for received items
    3. Adds expenses to jobs' reality pricing
    
    Args:
        purchase_order_id: The ID of the purchase order
        received_quantities: Dict mapping line item IDs to received quantities
        
    Returns:
        bool: True if successful, False otherwise
    """
    logger.warning("DELIVERY RECEIPT SERVICE: This service is still in development and needs testing!")
    logger.debug("Starting delivery receipt processing...")
    
    try:
        with transaction.atomic():
            # Get the purchase order
            purchase_order = PurchaseOrder.objects.get(id=purchase_order_id)
            logger.debug(f"Found PO {purchase_order.po_number}")
            
            # Track total received quantities for PO status update
            total_received = 0
            total_ordered = 0
            
            # Process each line item
            for line_id, received_qty in received_quantities.items():
                logger.debug(f"Processing line item {line_id} with quantity {received_qty}")
                line = PurchaseOrderLine.objects.get(id=line_id)
                received_qty = Decimal(str(received_qty))
                
                # Validate received quantity
                if received_qty > line.quantity:
                    logger.warning(f"Received quantity ({received_qty}) exceeds ordered quantity ({line.quantity}) for line {line.description}")
                    raise ValueError(f"Received quantity ({received_qty}) cannot exceed ordered quantity ({line.quantity}) for line {line.description}")
                
                # Update line item
                logger.debug(f"Updating line item {line_id} with received quantity {received_qty}")
                line.received_quantity = received_qty
                line.save()
                
                # Create stock entry
                if received_qty > 0:
                    logger.debug(f"Creating stock entry for line {line_id}")
                    # TODO: Need to verify stock model fields and requirements
                    logger.warning("Stock creation needs verification of model fields and requirements")
                    Stock.objects.create(
                        job=line.job,
                        description=line.description,
                        quantity=received_qty,
                        unit_cost=line.unit_cost,
                        date=timezone.now(),
                        source="purchase_order",
                        source_id=purchase_order.id,
                        notes=f"Received from PO {purchase_order.po_number}"
                    )
                    
                    # Add to job's reality pricing
                    if line.job:
                        logger.debug(f"Adding expense to job {line.job.id} for line {line_id}")
                        # TODO: Need to verify job pricing model fields and requirements
                        logger.warning("Job pricing creation needs verification of model fields and requirements")
                        JobPricing.objects.create(
                            job=line.job,
                            category="material",
                            description=f"Received: {line.description}",
                            quantity=received_qty,
                            unit_cost=line.unit_cost,
                            total_cost=received_qty * line.unit_cost,
                            date=timezone.now(),
                            source="purchase_order",
                            source_id=purchase_order.id
                        )
                    else:
                        logger.warning(f"Line item {line_id} has no associated job - skipping job pricing")
                
                total_received += received_qty
                total_ordered += line.quantity
            
            # Update PO status
            logger.debug(f"Updating PO status - total received: {total_received}, total ordered: {total_ordered}")
            if total_received == 0:
                purchase_order.status = 'submitted'
            elif total_received < total_ordered:
                purchase_order.status = 'partially_received'
            else:
                purchase_order.status = 'fully_received'
            
            purchase_order.save()
            
            logger.info(f"Successfully processed delivery receipt for PO {purchase_order.po_number}")
            logger.warning("DELIVERY RECEIPT SERVICE: This service needs thorough testing before production use!")
            return True
            
    except Exception as e:
        logger.error(f"Error processing delivery receipt for PO {purchase_order_id}: {str(e)}")
        logger.warning("DELIVERY RECEIPT SERVICE: Error occurred - service needs testing and error handling improvements")
        raise 