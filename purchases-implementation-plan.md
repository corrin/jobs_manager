# Materials Management Implementation Plan

This document outlines our approach to implementing the materials management system in sequential, testable steps. Each step delivers business value and builds toward the complete solution.

## Understanding The Current State

The system already has:
- Developed `PurchaseOrder` and `PurchaseOrderLine` models:
    - `PurchaseOrder` includes status tracking (`draft`, `submitted`, `partially_received`, `fully_received`, `void`) and Xero integration fields.
    - `PurchaseOrderLine` includes association with a specific `Job` and tracks `received_quantity`.
- Delivery Receipt Tracking: Implemented via the `MaterialEntry` model. When items are received against a `PurchaseOrderLine` (likely via a delivery receipt process), `MaterialEntry` records are created, linking the received item to both the `PurchaseOrderLine` and a specific `JobPricing` record. This replaces the originally planned separate `Purchase`/`PurchaseLine` models.
- Integration with `Client` model (used as suppliers) confirmed.
- General Stock Management (as described in Phase 4) appears **not implemented**. The `MaterialEntry` model tracks materials linked to specific jobs/pricing, not general inventory.

## Requirements Overview

1. **Purchase Order Creation**
   - Dedicated "Purchases" page
   - "New Purchase" form
   - PO has supplier, PO number, date raised
   - Line items with job ID, material description, quoted price
   - Xero integration (optional)

2. **Delivery Confirmation**
   - Mark PO as delivered
   - Validation against delivery docket

3. **Invoice Processing**
   - Match invoice to PO
   - Mark as "ok for payment"
   - Update Xero status

4. **Stock Management**
   - Create stock items from purchases
   - Split stock functionality
   - Assign stock to jobs

## Implementation Roadmap

### Phase 1: Purchase Order Basic Functionality

#### Ticket 1.1: Update Purchase Order Line Model [COMPLETED]
*Job field added to `PurchaseOrderLine` model.*

#### Ticket 1.2: Create Purchase Order List View [COMPLETED]
*List view (`PurchaseOrderListView`) and URL (`/purchase-orders/`) implemented.*

#### Ticket 1.3: Create Purchase Order Form [COMPLETED & EXTENDED]
*Create/Edit view (`PurchaseOrderCreateView`) and URLs (`/purchase-orders/new/`, `/purchase-orders/<uuid:pk>/`) implemented. Includes autosave functionality (`/api/autosave-purchase-order/`).*

#### Ticket 1.4: Purchase Order Detail View [IMPLEMENTED DIFFERENTLY]
*No dedicated detail view found. Viewing PO details is likely handled by the create/edit view (`PurchaseOrderCreateView`) via the `/purchase-orders/<uuid:pk>/` URL.*

### Phase 2: Delivery Confirmation

#### Ticket 2.1: Add Delivery Status Tracking to PurchaseOrder [IMPLEMENTED DIFFERENTLY]
*Delivery status tracked via `status` field on `PurchaseOrder` and `received_quantity` on `PurchaseOrderLine`, not a simple boolean flag.*

#### Ticket 2.2: Create Delivery Confirmation Interface [IMPLEMENTED DIFFERENTLY / LIKELY COMPLETE]
- **Description:** Create UI for confirming delivery of items against a Purchase Order.
- **Status:** Implemented differently. Delivery confirmation appears handled by creating `MaterialEntry` records, likely via a dedicated "Delivery Receipt" form/view (`delivery_receipt_form.html`, `delivery_receipt_service.py`). This links received items to `PurchaseOrderLine` and `JobPricing`. The `PurchaseOrder` status (`partially_received`, `fully_received`) and `PurchaseOrderLine.received_quantity` are likely updated as part of this process.
- **Technical Details (Original Plan):**
  - Add delivery toggle to purchase order detail page
  - Create view to handle delivery confirmation
  - Add URL route for status update
- **Technical Details (Actual Implementation - Inferred):**
  - Create Delivery Receipt view/form.
  - Logic in `delivery_receipt_service.py` to create `MaterialEntry` records.
  - Update `PurchaseOrder.status` and `PurchaseOrderLine.received_quantity`.
- **Testing:**
  - Create a PO.
  - Use the Delivery Receipt process to receive items against the PO.
  - Verify `MaterialEntry` records are created correctly.
  - Verify `PurchaseOrder` status and `PurchaseOrderLine.received_quantity` are updated.
  - Verify UI reflects the received status.
- **Estimated Time:** 3 hours (Original Estimate)

### Phase 3: Invoice Processing

#### Ticket 3.1: Add Invoice Matching to PurchaseOrder [NOT IMPLEMENTED]
- **Description:** Allow linking an invoice/bill to a purchase order.
- **Status:** Not implemented. No direct relationship (e.g., ForeignKey) found between the `Bill` and `PurchaseOrder` models. Matching is likely manual or handled outside the core models.
- **Technical Details:**
  - Ensure relationship exists between PurchaseOrder and Bill
  - Create UI for matching invoices to purchase orders
- **Testing:**
  - Open a purchase order
  - Link to an existing invoice/bill
  - Verify relationship is established
- **Estimated Time:** 3 hours (Original Estimate)

#### Ticket 3.2: Create Invoice Approval Workflow [IMPLEMENTED]
*Approval handled via the `status` field on the `Bill` model, using the `AUTHORISED` state from the `InvoiceStatus` enum.*

#### Ticket 3.3: Update Xero Integration [NOT IMPLEMENTED]
- **Description:** Update invoice/bill status in Xero when changed locally (e.g., marked as AUTHORISED).
- **Status:** Not implemented. Current Xero integration appears focused on creating/deleting documents and syncing data *from* Xero, not pushing status updates *to* Xero.
- **Technical Details:**
  - Extend existing Xero API integration
  - Add status update functionality
- **Testing:**
  - Mark an invoice as approved
  - Verify status changes in Xero
- **Estimated Time:** 4 hours

### Phase 4: Stock Management (Revised Workflow: PO -> Stock -> Job)

*This phase implements a stock system where received PO items create Stock records, potentially allocated across multiple jobs or general stock. Job costing occurs when Stock is consumed.*

#### Ticket 4.1: Refine Stock & MaterialEntry Models
- **Description:** Review and update the `Stock` and `MaterialEntry` models for the new workflow relationships.
- **Technical Details:**
  - **Stock Model (`workflow/models/stock.py`):**
    - Ensure `source_id` stores `PurchaseOrderLine.id` (change type if needed, ensure it's indexed).
    - Remove the existing `Stock.split()` method (splitting now handled via allocation on receipt).
  - **MaterialEntry Model (`workflow/models/material_entry.py`):**
    - Add `source_stock` ForeignKey field linking to `Stock` (nullable=True, blank=True initially for existing data).
    - Make `purchase_order_line` field nullable (`null=True`, `blank=True`) as the primary link is now via `source_stock`.
  - Create migrations for both models.
- **Testing:** Verify model changes and migrations.

#### Ticket 4.2: Use Existing 'Worker Admin' Job for Stock
- **Description:** Utilize the "Worker Admin" job, guaranteed to exist via the `create_shop_jobs` command, for general stock.
- **Technical Details:**
  - Code needing the general stock job will query directly: `Job.objects.get(name="Worker Admin")`.
  - No special error handling needed for non-existence, as the command ensures it exists. A `DoesNotExist` error indicates a setup issue.
- **Testing:** Verify direct lookup retrieves the correct job instance.

#### Ticket 4.3: Update Delivery Receipt UI (Allocation - YNAB Style)
- **Description:** Modify the delivery receipt form (`delivery_receipt_form.html` and JS) to handle allocation of received items, inspired by YNAB/Actual Budget splitting.
- **Technical Details:**
  - When an item moves to "Received":
    - Default `Quantity Received` to ordered quantity (user can override if delivery differs).
    - Display as a single row representing the full received item, tentatively allocated to the `PurchaseOrderLine.job`.
  - Add a "Split Allocation" button to this row.
  - Clicking "Split Allocation":
    - Dynamically replaces the single row with multiple, linked allocation rows.
    - Each allocation row allows specifying: Target Job selector (including 'Worker Admin' job) and Quantity allocated.
    - UI must enforce that the sum of allocated quantities equals the total Quantity Received.
  - Update JS to manage this dynamic row replacement/addition and collect the final allocation data (list of {target_job_id, quantity} per original received item) for submission.
- **Testing:** Verify default state, split button reveals allocation rows, quantity validation works, data submission format is correct.

#### Ticket 4.4: Update Delivery Receipt Service (Stock Creation)
- **Description:** Rewrite the `process_delivery_receipt` service (`delivery_receipt_service.py`) to create `Stock` records based on UI allocations.
- **Technical Details:**
  - Modify service input to accept allocation data (target job, quantity per allocation).
  - For each allocation row:
    - Create a `Stock` record with allocated quantity, original unit cost, target job ('Worker Admin' or specific job), source='purchase_order', source_id=`PurchaseOrderLine.id`.
  - Remove old `MaterialEntry` creation logic from this service.
  - Update `PurchaseOrderLine.received_quantity` based on total received.
- **Testing:** Verify correct `Stock` records are created for default and split allocations.

#### Ticket 4.5: Implement Stock Consumption UI
- **Description:** Create UI for users to consume stock for a specific job.
- **Technical Details:**
  - Likely on the Job detail page or a related tab/modal.
  - Allow selecting `Stock` items (filter for items linked to this job OR the 'Worker Admin' job).
  - Input field for "Quantity Used" from the selected stock item.
- **Testing:** Verify UI allows selecting stock and entering quantity used.

#### Ticket 4.6: Implement Stock Consumption Logic (Job Costing)
- **Description:** Create the backend service/view to handle stock consumption and apply job costs.
- **Technical Details:**
  - Takes Job ID, Stock ID, Quantity Used as input.
  - Creates a `MaterialEntry` linked to the Job's 'Reality' pricing.
    - Set `MaterialEntry.source_stock` to the consumed `Stock` record ID.
    - Set `MaterialEntry.quantity` = Quantity Used.
    - Set `MaterialEntry.unit_cost` from `Stock.unit_cost`.
    - Calculate `MaterialEntry.unit_revenue`/total cost based on pricing rules (e.g., half-sheet rule) applied to Quantity Used.
    - Leave `MaterialEntry.purchase_order_line` null (traceability is via `source_stock`).
  - Reduce the quantity of the source `Stock` record. Handle zero quantity (mark inactive?).
- **Testing:** Verify `MaterialEntry` is created with correct cost, `source_stock` link, and null `purchase_order_line`. Verify `Stock` quantity is reduced. Test pricing rules.

#### Ticket 4.7: Basic Stock List View
- **Description:** Create a simple view to display current stock levels.
- **Technical Details:**
  - Create `StockListView` and template.
  - Display `Stock` items, showing description, quantity, unit cost, associated job ('Worker Admin' or specific job).
  - Add basic filtering (e.g., by description, by job).
  - Add URL and navigation link.
- **Testing:** Verify stock items are displayed correctly.

## Testing Strategy

For each ticket:

1. **Developer Testing:**
   - Unit tests for models and core logic
   - Manual testing of UI flows

2. **User Acceptance Testing:**
   - Test with real-world scenarios
   - Verify business requirements are met

3. **Integration Testing:**
   - Test end-to-end flows across multiple components
   - Ensure Xero integration works correctly

## Risks and Mitigation

1. **Data Integrity:** Ensure transactions are atomic, especially for stock splitting
2. **Xero Integration:** Test thoroughly with sandbox before production
3. **User Adoption:** Create clear documentation and provide training

## Next Steps After Implementation

1. **Refinement:** Gather feedback and improve UI/UX
2. **Reporting:** Develop inventory reports
3. **Advanced Features:** Consider barcode scanning, automated reordering 