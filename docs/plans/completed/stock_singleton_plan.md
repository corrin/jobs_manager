# Stock Singleton + Stock Movement Plan

## Context
- Current delivery receipt flow creates a new Stock row for every PO line allocation.
- We need a single Stock instance per item_code, updated over time, while preserving movement history.
- Add StockMovement to register each receipt/consumption/adjustment with metadata.

## Goals
- Prevent duplicate Stock rows for the same item_code.
- Keep a clear audit trail of quantity/cost changes and source references.
- Preserve current CostLine ext_refs behavior and Xero sync expectations.
- Always auto-generate item_code when missing.

## Proposed Data Model
- Stock (existing)
  - Enforce singleton per item_code (item_code is the unique identity; no location splits).
  - Add derived fields if needed (e.g., last_received_at).
- StockMovement (new)
  - Fields:
    - id (UUID)
    - stock (FK -> Stock)
    - movement_type (choices: receipt, consume, adjust, split, merge)
    - quantity_delta (Decimal; positive receipt, negative consume)
    - unit_cost (Decimal, nullable)
    - unit_revenue (Decimal, nullable)
    - source (choices aligned to Stock.source + "costline_consume")
    - source_purchase_order_line (FK, nullable)
    - source_cost_line (FK, nullable)
    - source_parent_stock (FK, nullable) for splits/merges
    - metadata (JSON) for allocation metadata (metal_type, alloy, location, etc.)
    - created_at (DateTime)
  - Constraint: if movement_type == receipt, require source_purchase_order_line.

## Service-Level Changes
1) Normalize item_code resolution
   - Always auto-generate item_code when missing, before any stock creation/update.
   - Persist the generated item_code immediately so all flows converge.
2) Receipt allocations
   - Replace _create_stock_from_allocation with get-or-update:
     - select_for_update on Stock by item_code.
     - if exists: update quantity only; Stock.unit_cost remains the default set by first item with this code.
     - if not: create Stock with unit_cost as the default price for this item_code.
     - create StockMovement receipt row with full details.
3) Consumption
   - In stock_service.consume_stock, create StockMovement consume row.
4) Merge/dedupe
   - Extend merge_stock_into to create StockMovement merge row.

## Data Migration / Cleanup
- Add migration to create StockMovement table.
- Add one-time management command to:
  - Find duplicate Stock rows by item_code.
  - Merge into earliest active row using merge_stock_into.
  - Backfill StockMovement for existing Stock rows (best-effort).

## API/Serializer Updates (if needed)
- Decide if StockMovement is exposed to frontend or kept internal.
- If exposed: add read-only serializer and endpoint for movement history.

## Validation & Testing
- Manual checklist:
  - Create two PO lines with same item_code, receive allocations twice.
  - Confirm single Stock row with updated quantity.
  - Confirm StockMovement receipt rows added.
  - Consume stock and confirm StockMovement consume row + CostLine ext_refs.
  - Run Xero sync and verify item_code lookup intact.

### Implementation Plan
- Model + migration
  - Add StockMovement model with FK to Stock, movement type, quantity delta, unit_cost/unit_revenue, source refs, metadata, created_at.
  - Create migration for new table and constraints (e.g., receipt requires source_purchase_order_line).
- Item code generation (single source of truth)
  - Add a helper to always generate item_code when missing and persist immediately.
  - Ensure all stock-creating flows call it before any Stock create/update.
- Delivery receipt flow (singleton by item_code)
  - Replace _create_stock_from_allocation with get-or-update by item_code using select_for_update.
  - If stock exists: only increment quantity and leave Stock.unit_cost untouched.
  - If not: create Stock with unit_cost as the default for that item_code.
  - Always create a StockMovement receipt entry with raw allocation values.
- Stock consumption flow
  - After quantity change, write a StockMovement entry for consumption.
- Merge/dedupe
  - Extend merge_stock_into to create a StockMovement merge entry and preserve references.
  - Add a management command to merge duplicates by item_code and backfill movements (best effort).
