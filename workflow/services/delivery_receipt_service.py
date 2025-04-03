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

# Define a custom exception for validation errors during processing
class DeliveryReceiptValidationError(ValueError):
    pass

def process_delivery_receipt(purchase_order_id: str, line_allocations: dict) -> bool:
    """
    Process a delivery receipt for a purchase order based on detailed line allocations.

    This function:
    1. Validates the submitted allocation data for each PO line.
    2. Updates the received quantity on each PurchaseOrderLine.
    3. Deletes any previous Stock entries originating from these PO lines for this PO.
    4. Creates new Stock entries based on the provided allocations (linking to target jobs or stock holding job).
    5. Updates the overall PurchaseOrder status.

    Args:
        purchase_order_id: The ID of the purchase order being received.
        line_allocations: A dictionary where keys are PurchaseOrderLine IDs (str)
                          and values are dicts containing:
                          {
                              "total_received": float | str,
                              "allocations": [
                                  {"job_id": str, "quantity": float | str},
                                  ...
                              ]
                          }

    Returns:
        bool: True if successful.

    Raises:
        DeliveryReceiptValidationError: If validation fails (e.g., allocation mismatch, invalid job ID).
        PurchaseOrder.DoesNotExist: If the purchase_order_id is invalid.
        PurchaseOrderLine.DoesNotExist: If a line_id in the input is invalid.
        Job.DoesNotExist: If a job_id in the allocations is invalid.
        Exception: For other unexpected errors during processing.
    """
    logger.info(f"Starting delivery receipt processing for PO ID: {purchase_order_id}")
    logger.debug(f"Received line_allocations data: {line_allocations}")

    try:
        with transaction.atomic():
            purchase_order = PurchaseOrder.objects.select_related('supplier').get(id=purchase_order_id)
            logger.debug(f"Found PO {purchase_order.po_number}")

            # Log unexpected PO statuses but proceed (unless DoesNotExist error occurred)
            # Errors for draft/void should ideally be caught before reaching this service
            if purchase_order.status not in ['submitted', 'partially_received', 'fully_received']:
                 logger.warning(f"Processing delivery receipt for PO {purchase_order.po_number} which has an unexpected status: {purchase_order.status}. This might indicate an issue elsewhere.")

            processed_line_ids = set(line_allocations.keys())

            # Pre-fetch lines and jobs for efficiency and validation
            lines = { str(line.id): line for line in PurchaseOrderLine.objects.filter(id__in=processed_line_ids, purchase_order=purchase_order) }
            if len(lines) != len(processed_line_ids):
                 missing_lines = processed_line_ids - set(lines.keys())
                 raise DeliveryReceiptValidationError(f"Invalid or mismatched PurchaseOrderLine IDs provided: {missing_lines}")

            all_job_ids = set()
            for line_data in line_allocations.values():
                for alloc in line_data.get("allocations", []):
                    if alloc.get("job_id"):
                        all_job_ids.add(alloc["job_id"])

            jobs = { str(job.id): job for job in Job.objects.filter(id__in=all_job_ids) }
            if len(jobs) != len(all_job_ids):
                 missing_jobs = all_job_ids - set(jobs.keys())
                 raise DeliveryReceiptValidationError(f"Invalid Job IDs provided in allocations: {missing_jobs}")

            # --- Process each submitted line ---
            for line_id, line_data in line_allocations.items():
                line = lines[line_id]
                logger.debug(f"Processing line: {line.id} ({line.description})")

                # Validate total_received
                try:
                    total_received = Decimal(str(line_data.get("total_received", 0)))
                    if total_received < 0:
                         raise DeliveryReceiptValidationError(f"Negative total received quantity not allowed for line {line.id}.")
                except (InvalidOperation, TypeError):
                     raise DeliveryReceiptValidationError(f"Invalid total received quantity format for line {line.id}.")

                allocations = line_data.get("allocations", [])
                calculated_allocation_sum = Decimal('0.0')
                valid_allocations = []

                # Validate individual allocations
                for alloc in allocations:
                    try:
                        alloc_qty = Decimal(str(alloc.get("quantity", 0)))
                        job_id = alloc.get("job_id")
                        if alloc_qty < 0:
                             raise DeliveryReceiptValidationError(f"Negative allocation quantity not allowed for line {line.id}.")
                        if alloc_qty > 0: # Only process non-zero allocations
                             if not job_id:
                                 raise DeliveryReceiptValidationError(f"Missing job ID for non-zero allocation quantity on line {line.id}.")
                             if job_id not in jobs:
                                 raise DeliveryReceiptValidationError(f"Invalid job ID '{job_id}' in allocation for line {line.id}.")
                             calculated_allocation_sum += alloc_qty
                             valid_allocations.append({'job': jobs[job_id], 'quantity': alloc_qty})
                    except (InvalidOperation, TypeError):
                        raise DeliveryReceiptValidationError(f"Invalid allocation quantity format for line {line.id}.")

                # Validate sum vs total
                if abs(calculated_allocation_sum - total_received) > Decimal('0.001'):
                    raise DeliveryReceiptValidationError(
                        f"Allocation quantity mismatch for line '{line.description}' (Line ID: {line.id}). "
                        f"Total Received: {total_received}, Sum of Allocations: {calculated_allocation_sum}."
                    )

                # --- Passed Validation - Update Database ---
                # Delete previous stock for this line
                deleted_count, _ = Stock.objects.filter(
                    source='purchase_order',
                    source_purchase_order_line=line
                ).delete()
                if deleted_count > 0:
                    logger.debug(f"Deleted {deleted_count} existing stock entries for line {line.id}.")

                # Update PO Line received quantity
                line.received_quantity = total_received
                line.save(update_fields=['received_quantity']) # Be specific
                logger.debug(f"Updated line {line.id} received_quantity to {total_received}.")

                # Create new Stock entries
                for alloc_data in valid_allocations:
                    target_job = alloc_data['job']
                    alloc_qty = alloc_data['quantity']
                    stock_item = Stock.objects.create(
                        job=target_job,
                        description=line.description,
                        quantity=alloc_qty,
                        unit_cost=line.unit_cost or Decimal('0.00'),
                        date=timezone.now(),
                        source='purchase_order',
                        source_purchase_order_line=line,
                        notes=f"Received from PO {purchase_order.po_number}"
                    )
                    logger.debug(f"Created Stock entry {stock_item.id} for line {line.id}, allocated to Job {target_job.id}, qty {alloc_qty}.")

            # --- Update Overall PO Status ---
            all_po_lines = purchase_order.po_lines.all() # Re-fetch needed? Or can we trust the loop? Re-fetch is safer.
            current_total_ordered = sum(l.quantity for l in all_po_lines)
            current_total_received = sum(l.received_quantity for l in all_po_lines)

            logger.debug(f"Updating PO status - Current Total Received: {current_total_received}, Current Total Ordered: {current_total_ordered}")
            new_status = purchase_order.status # Default to current
            if current_total_received <= 0:
                 if purchase_order.status != 'void': # Avoid changing voided status
                     new_status = 'submitted'
            elif current_total_received < current_total_ordered:
                new_status = 'partially_received'
            else: # received >= ordered
                new_status = 'fully_received'

            if new_status != purchase_order.status:
                 purchase_order.status = new_status
                 purchase_order.save(update_fields=['status'])
                 logger.debug(f"Set PO {purchase_order.po_number} status to {purchase_order.status}")
            else:
                 logger.debug(f"PO {purchase_order.po_number} status remains {purchase_order.status}")


            logger.info(f"Successfully processed delivery receipt allocations for PO {purchase_order.po_number}")
            return True

    except DeliveryReceiptValidationError as ve:
         logger.error(f"Validation Error processing delivery receipt for PO {purchase_order_id}: {ve}")
         raise # Re-raise validation errors to be caught by the view
    except Exception as e:
        logger.exception(f"Unexpected Error processing delivery receipt for PO {purchase_order_id}: {str(e)}")
        raise Exception(f"An unexpected error occurred: {str(e)}")