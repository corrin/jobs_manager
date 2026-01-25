# Stock Movement Model Refactor Plan

Author: Codex (2026-01-25)
Context: Replace implicit quantity-on-row logic with an auditable stock movement ledger, keeping the existing `Stock` record as the item definition/template.

## Goals
- Eliminate duplicate stock rows by treating quantity as the sum of movements, not a mutable field.
- Provide a complete audit trail (who, when, why) for every stock change.
- Keep Xero sync and CostLine links intact, with clearer identity for items.
- Support future operations: transfers, splits/offs, adjustments, and unit cost evolution.

## Proposed Domain Model

### Core tables
1) **StockItem** (existing `purchasing.Stock`, trimmed to definition/identity)
   - Identity: `id`, `item_code` (unique), `description`, `metal_type`, `alloy`, `specifics`, `location` (optional), `source` (po/manual/catalog), `job` (stock-holding by default), `unit_cost_estimate`, `unit_revenue_estimate`, `xero_id`, `metadata/ext_refs`.
   - No `quantity` field (derived).
   - Still keeps `source_purchase_order_line` + `active_source_purchase_order_line_id` for traceability and uniqueness per PO line.

2) **StockMovement**
   - `id` (uuid), `stock_item` FK, `movement_type` (receipt, consume, transfer_out, transfer_in, adjust_up, adjust_down, split_out, split_in, reversal), `quantity` (signed Decimal, >0 stored, direction via type), `unit_cost`, `unit_revenue` (optional), `actor` (staff/user), `job` (for consumption/transfer targets), `reference` (generic string), `ext_refs` JSON (po_line_id, costline_id, xero_item_id, source_movement_id for reversals), `meta` JSON, `occurred_at` (ts), `created_at`.
   - DB index on `(stock_item, occurred_at)` and `(stock_item, created_at)` for fast balances.
   - Soft delete **not** allowed; use reversal movement instead.

3) **StockBalance (materialized view / cached table)**
   - Optional performance layer: per `stock_item` aggregate of `quantity`, `avg_unit_cost` (moving weighted average), `updated_at`.
   - Refreshed via triggers or nightly job; write-through recompute inside the same transaction on new movement.

### Derived quantity
- `StockItem.available_quantity` = SUM of `StockMovement.quantity * direction` for that item (direction implied by type).
- Negative balances allowed only for `consume` with explicit flag; otherwise block at validation.

## Flow Changes
- **Receipt (PO delivery)**: create `stock_item` if missing, then `receipt` movement with quantity and unit_cost. No direct field updates on item.
- **Manual add/stocktake**: `adjust_up` or `adjust_down` movement with reason in `meta`.
- **Consume**: create `consume` movement; attach `job`, create `CostLine` and link via `ext_refs.costline_id`.
- **Transfer**: two movements (`transfer_out` from source, `transfer_in` to destination), sharing a `reference`/`ext_refs.transfer_id`.
- **Split/offs**: create new `StockItem` child (or reuse metadata), emit `split_out` on parent and `split_in` on child.
- **Reversal**: new movement with `movement_type=reversal`, points to original movement id in `ext_refs.source_movement_id`, quantity mirrors original.

## API & Service Adjustments
- `POST /purchasing/rest/stock/`: create `StockItem` (definition) and an initial `receipt` movement.
- `POST /purchasing/rest/stock/{id}/consume/`: create movement + cost line; quantity derived, no direct `StockItem.quantity` mutation.
- List endpoints should expose `available_quantity` (computed) and recent movement summary.
- Add movement listing endpoint: `/purchasing/rest/stock/{id}/movements/` with pagination.

## Data Integrity & Concurrency
- All mutations wrapped in `transaction.atomic()` with `select_for_update` on `StockItem`.
- Prevent concurrent double-receipts by unique constraint: one active `StockItem` per `source_purchase_order_line`.
- Movement-level validation: `receipt/adjust_up/split_in/transfer_in` add, `consume/transfer_out/split_out/adjust_down` subtract; block if resulting quantity < 0 unless `allow_negative=True`.
- `persist_app_error` on all catch blocks; no silent fallbacks.

## Migration Plan (phased)
1) **Schema**: add `StockMovement` table and optional `StockBalance` cache; add read-only property to `StockItem` to surface computed quantity.
2) **Dual write** (transition):
   - Keep `Stock.quantity` as-is for compatibility; each write also records a movement and recomputes balance; reconciliation job to detect drift.
3) **Backfill**:
   - For each `Stock` row, create an initial `receipt` movement equal to current `quantity` and `unit_cost`.
   - For each `CostLine.ext_refs.stock_id`, ensure a corresponding `consume` movement exists; create placeholder if missing.
4) **Switch read path**:
   - API/serializers use movement-derived quantity.
   - Deprecate direct writes to `Stock.quantity`.
5) **Cleanup**:
   - Drop/ignore `Stock.quantity` once confidence high; tighten validation to forbid direct updates.

## Reporting & Sync
- Xero sync uses `StockItem` fields + movement-derived `available_quantity`.
- Month-end and costing reports pull from `StockBalance` or live aggregates; ensure indexes for SUM queries.

## Risks / Mitigations
- **Performance**: movement aggregation could be heavy; use DB-side SUM with index or cached balance table.
- **Drift during transition**: run nightly reconciliation comparing `Stock.quantity` vs movement sum; alert on mismatches.
- **API contract changes**: coordinate frontend; keep `quantity` field but mark as derived/read-only until removed.

## Open Questions
- Do we need per-location sub-balances? (If yes, include `location` on movement and aggregate by location.)
- Should `unit_cost` be mandatory on consume? (If missing, use moving average.)
- How to handle tax/markup differences per job during transfers?

## Acceptance / Manual Validation Checklist
- Create same item twice via API → single `StockItem`, two `receipt` movements, correct summed quantity.
- Consume after refactor → quantity decreases via movement; CostLine linked.
- Transfer between locations → balanced out/in pair, net zero across both items.
- Backfill script produces zero-drift: legacy `Stock.quantity` == movement sum.
