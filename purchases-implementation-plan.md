# Materials Management Implementation Plan

This document outlines our approach to implementing the materials management system in sequential, testable steps. Each step delivers business value and builds toward the complete solution.

## Understanding The Current State

The system already has:
- Basic `PurchaseOrder` and `PurchaseOrderLine` models
- `Purchase` and `PurchaseLine` models for tracking deliveries
- Integration with Clients model (used as suppliers)

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

#### Ticket 1.1: Update Purchase Order Line Model
- **Description:** Update the PurchaseOrderLine model to associate each line with a specific job
- **Technical Details:**
  - Add job field to PurchaseOrderLine model 
  - Create migration
- **Testing:** 
  - Verify migration runs successfully
  - Check in Django admin that the field exists
- **Estimated Time:** 1 hour

#### Ticket 1.2: Create Purchase Order List View
- **Description:** Create a view to list all purchase orders
- **Technical Details:**
  - Create a PurchasesListView
  - Create template for listing purchase orders
  - Add URL route
  - Add navigation link in main menu
- **Testing:**
  - Navigate to the Purchases page
  - Verify any existing purchase orders are displayed
  - Check that navigation from main menu works
- **Estimated Time:** 2 hours

#### Ticket 1.3: Create Purchase Order Form
- **Description:** Create a form for creating new purchase orders
- **Technical Details:**
  - Create PurchaseOrderForm and PurchaseOrderLineForm
  - Create PurchaseOrderCreateView with form handling
  - Implement form template with line item management
  - Add URL route 
- **Testing:**
  - Navigate to New Purchase from Purchases page
  - Create a purchase order with at least one line item
  - Verify data is saved correctly
  - Verify job association with line items works
- **Estimated Time:** 4 hours

#### Ticket 1.4: Purchase Order Detail View
- **Description:** Create a view to see purchase order details
- **Technical Details:**
  - Create PurchaseDetailView
  - Create detail template
  - Add URL route
- **Testing:**
  - Create a purchase order
  - Click on view details
  - Verify all information displays correctly
  - Verify line items are shown with correct job associations
- **Estimated Time:** 2 hours

### Phase 2: Delivery Confirmation

#### Ticket 2.1: Add Delivery Flag to PurchaseOrder
- **Description:** Add a boolean field to mark purchase orders as delivered
- **Technical Details:**
  - Add a 'delivered' field to the PurchaseOrder model
  - Create migration
- **Testing:**
  - Verify migration runs successfully
  - Check in Django admin that the field exists
- **Estimated Time:** 1 hour

#### Ticket 2.2: Create Delivery Confirmation Interface
- **Description:** Create UI for marking orders as delivered
- **Technical Details:**
  - Add delivery toggle to purchase order detail page
  - Create view to handle delivery confirmation
  - Add URL route for status update
- **Testing:**
  - Open a purchase order details
  - Mark as delivered
  - Verify status updates in the database
  - Verify UI reflects the change
- **Estimated Time:** 3 hours

### Phase 3: Invoice Processing

#### Ticket 3.1: Add Invoice Matching to PurchaseOrder
- **Description:** Allow linking an invoice to a purchase order
- **Technical Details:**
  - Ensure relationship exists between PurchaseOrder and Bill
  - Create UI for matching invoices to purchase orders
- **Testing:**
  - Open a purchase order
  - Link to an existing invoice/bill
  - Verify relationship is established
- **Estimated Time:** 3 hours

#### Ticket 3.2: Create Invoice Approval Workflow
- **Description:** Allow marking invoices as "ok for payment"
- **Technical Details:**
  - Add approval field to Bill model
  - Add approval UI in invoice detail page
  - Create view to handle approval
- **Testing:**
  - Open a matched invoice
  - Mark as "ok for payment"
  - Verify status updates
- **Estimated Time:** 3 hours

#### Ticket 3.3: Update Xero Integration
- **Description:** Update invoice status in Xero
- **Technical Details:**
  - Extend existing Xero API integration
  - Add status update functionality
- **Testing:**
  - Mark an invoice as approved
  - Verify status changes in Xero
- **Estimated Time:** 4 hours

### Phase 4: Stock Management

#### Ticket 4.1: Create Stock Model
- **Description:** Create the basic Stock model
- **Technical Details:**
  - Create Stock model with fields for tracking inventory
  - Create migration
- **Testing:**
  - Verify migration runs successfully
  - Check in Django admin that the model exists
- **Estimated Time:** 2 hours

#### Ticket 4.2: Stock List View
- **Description:** Create a view to list all stock items
- **Technical Details:**
  - Create StockListView
  - Create template for listing stock
  - Add URL route
  - Add navigation link
- **Testing:**
  - Navigate to Stock page
  - Verify items display correctly
- **Estimated Time:** 2 hours

#### Ticket 4.3: Auto-Create Stock from Purchases
- **Description:** Automatically create stock items when purchase is received
- **Technical Details:**
  - Add signal or method to create stock entries when a purchase is marked as delivered
  - Ensure proper data flow from purchase to stock
- **Testing:**
  - Mark a purchase as delivered
  - Verify stock entries are created
- **Estimated Time:** 3 hours

#### Ticket 4.4: Stock Splitting Functionality
- **Description:** Allow splitting stock items into multiple items
- **Technical Details:**
  - Create StockSplitView
  - Create stock splitting form
  - Implement splitting logic with proper cost allocation
  - Add URL route
- **Testing:**
  - Select a stock item
  - Split it into two parts
  - Verify both parts exist with correct proportions
  - Verify costs are split proportionally
- **Estimated Time:** 6 hours

#### Ticket 4.5: Assign Stock to Jobs
- **Description:** Allow assigning stock items to jobs
- **Technical Details:**
  - Create UI for assigning stock to jobs
  - Create view to handle assignment
  - Add URL route
- **Testing:**
  - Select a stock item
  - Assign to a job
  - Verify assignment is saved
- **Estimated Time:** 3 hours

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