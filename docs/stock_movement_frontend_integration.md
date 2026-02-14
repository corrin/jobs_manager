# Frontend Integration: StockMovement-Based Stock Flow

This document describes the backend changes to stock handling and how the frontend should adapt. The goal is to treat `Stock` as the canonical item (singleton by `item_code`) and use `StockMovement` as the ledger for receipts, consumption, adjustments, splits, and merges.

## Summary of What Changed

- `Stock` is now a singleton per `item_code` (upserted in receipts/manual creation).
- `StockMovement` is the transactional record for stock changes (receipt/consume/adjust/merge/split).
- All references from cost lines and allocations should point to a **StockMovement ID**, not a `Stock` ID.
- Allocation flows (list/details/delete) use movement IDs (`allocation_id` = movement id).
- Delivery receipts, manual stock creation, and stock consumption now log movements.

## Data Contract Changes

### CostLine.ext_refs

- **Old**: `ext_refs.stock_id`
- **New**: `ext_refs.stock_movement_id`

If a material cost line consumes stock, it must reference the **consume movement** that represents the stock drawdown.

### Allocation ID

`allocation_id` for stock allocations now equals the **receipt StockMovement ID**.

This is used in:
- Allocation list for a PO
- Allocation details
- Allocation delete (stock allocations)

## API Behavior the Frontend Should Expect

### Delivery Receipt

When a receipt allocates to stock:
- The backend **upserts Stock by `item_code`**.
- It creates a **receipt StockMovement** for each allocation.
- The allocation list will return `allocation_id` = receipt movement id.

### Allocation List (Purchase Orders)

`GET /purchasing/rest/purchase-orders/{po_id}/allocations/`

- Stock allocations return a movement-based `allocation_id`.
- Use this ID for delete/details calls.

### Allocation Details

`GET /purchasing/rest/purchase-orders/{po_id}/allocations/{allocation_type}/{allocation_id}/details/`

- For `allocation_type=stock`, `allocation_id` must be the **receipt movement ID**.
- `can_delete` is false if there are **consume movements** for the same stock item.

### Allocation Delete

`POST /purchasing/rest/purchase-orders/{po_id}/allocations/{line_id}/delete/`

- For `allocation_type=stock`, `allocation_id` must be the **receipt movement ID**.
- The delete operation reverses the receipt by reducing stock quantity and deleting the receipt movement.

### Stock Consumption

Use either flow:

1. **Stock consume endpoint**
   `POST /purchasing/rest/stock/{stock_id}/consume/`
   - Backend creates a **consume StockMovement**.
   - The returned CostLine will include `ext_refs.stock_movement_id`.

2. **CostLine approval flow**
   - If approving a material CostLine, ensure `ext_refs.stock_movement_id` is set.
   - The backend will consume stock and replace any legacy `stock_id` reference.

### Stock List

`GET /purchasing/rest/stock/`

- Still returns Stock items (canonical record per `item_code`).
- Do **not** treat Stock rows as allocation records.

## Migration Notes

- Existing CostLines with `ext_refs.stock_id` are backfilled to:
  - Create a consume StockMovement
  - Replace `ext_refs.stock_id` with `ext_refs.stock_movement_id`
- Duplicate Stock rows are merged by `item_code` before the backfill.

## Frontend Checklist

- Replace any use of `ext_refs.stock_id` with `ext_refs.stock_movement_id`.
- Treat `allocation_id` for stock allocations as a **movement ID**.
- When storing or sending allocation references, store the movement ID.
- For consumption flows, rely on the returned `stock_movement_id` from the backend.

If you need a movement ID for a specific stock allocation, use the PO allocations endpoint rather than the stock list.
