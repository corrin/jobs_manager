from decimal import Decimal
from django.db import transaction
from django.utils import timezone
import logging

from workflow.models.purchase import PurchaseOrder, PurchaseOrderLine
from workflow.models.stock import Stock
from workflow.models.job import JobPricing
from workflow.models.material_entry import MaterialEntry
from workflow.models.company_defaults import CompanyDefaults
from workflow.enums import JobPricingStage

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

                # --- Handle Job Pricing (MaterialEntry) ---
                existing_material_entry = None # Initialize
                if line.job:
                    # Get the 'reality' pricing for the job
                    try:
                        reality_pricing = JobPricing.objects.get(
                            job=line.job,
                            pricing_stage=JobPricingStage.REALITY
                        )
                    except JobPricing.DoesNotExist:
                        logger.error(f"CRITICAL: 'Reality' JobPricing not found for job {line.job.id} while processing PO {purchase_order.po_number}, line {line.id}. Cannot modify material cost.")
                        raise ValueError(f"Reality pricing missing for job {line.job.id}")

                    # Find existing MaterialEntry for this PO line on this job
                    existing_material_entry = MaterialEntry.objects.filter(
                        job_pricing=reality_pricing,
                        purchase_order_line=line
                    ).first()

                    if received_qty > 0:
                        # Create or update MaterialEntry
                        if existing_material_entry:
                            logger.debug(f"Updating existing MaterialEntry for line {line_id} on job {line.job.id}")
                            existing_material_entry.quantity = received_qty
                            existing_material_entry.description = f"Received: {line.description}" # Keep description updated
                            existing_material_entry.save()
                        else:
                            logger.debug(f"Creating new MaterialEntry for line {line_id} on job {line.job.id}")
                            # Fetch company defaults to apply markup
                            defaults = CompanyDefaults.get_instance()
                            markup_multiplier = Decimal("1.0") + defaults.materials_markup
                            default_unit_revenue = (line.unit_cost * markup_multiplier).quantize(Decimal("0.01"))
                            
                            # Create the MaterialEntry and store it for potential stock check later
                            existing_material_entry = MaterialEntry.objects.create(
                                job_pricing=reality_pricing,
                                description=f"Received: {line.description}",
                                quantity=received_qty,
                                unit_cost=line.unit_cost,
                                unit_revenue=default_unit_revenue, # Set default revenue with markup
                                item_code=line.item_code,
                                purchase_order_line=line # Link to the PurchaseOrderLine
                            )
                    elif existing_material_entry:
                        # Received quantity is 0, remove the existing MaterialEntry
                        logger.debug(f"Received quantity is 0 for line {line_id}. Deleting existing MaterialEntry on job {line.job.id}")
                        existing_material_entry.delete()
                        existing_material_entry = None # Clear it as it's deleted

                else: # No associated job
                    logger.warning(f"Line item {line_id} has no associated job - skipping job pricing")


                # --- Handle Stock Entry ---
                # TODO: Refine stock handling - should we update/delete stock entries if quantity changes or becomes 0?
                # Current logic: Create stock if received_qty > 0 and no existing Stock entry found for this PO source/description/(job).
                
                should_create_stock = False
                if received_qty > 0:
                    # Check if a stock entry already exists for this specific receipt context
                    stock_filter_kwargs = {
                        "source": "purchase_order",
                        "source_id": purchase_order.id, # Assuming source_id links to PO Header
                        "description": line.description,
                        # Potentially add unit_cost or item_code if needed for uniqueness
                    }
                    if line.job:
                        stock_filter_kwargs["job"] = line.job
                    else:
                        stock_filter_kwargs["job__isnull"] = True # Explicitly check for no job

                    if not Stock.objects.filter(**stock_filter_kwargs).exists():
                        should_create_stock = True

                if should_create_stock:
                    logger.debug(f"Creating stock entry for line {line_id} (Job: {line.job.id if line.job else 'None'})")
                    logger.warning("Stock creation needs verification of model fields and requirements")
                    Stock.objects.create(
                        job=line.job, # Will be None if no job
                        description=line.description,
                        quantity=received_qty,
                        unit_cost=line.unit_cost,
                        date=timezone.now(),
                        source="purchase_order",
                        source_id=purchase_order.id, # Link to PO Header
                        # Consider linking to PO Line ID as well if needed for uniqueness/tracking
                        notes=f"Received from PO {purchase_order.po_number}"
                    )
                elif received_qty == 0:
                     # TODO: Add logic here to find and potentially delete the corresponding Stock entry
                     # Requires identifying the correct stock entry (e.g., using PO line ID if added to Stock model, or the filter args above)
                     logger.warning(f"Received quantity is 0 for line {line_id}. Corresponding Stock entry might need manual adjustment or deletion.")


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