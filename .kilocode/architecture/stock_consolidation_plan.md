# Stock Architecture Consolidation - Draft Plan

## Background / Current Pain Points
- Duplicate `Stock` rows per Purchase Order line lead to conflicting `xero_id` values and break sync. We currently rely on transactional locks + guards to mitigate symptoms.
- Item selector UX surfaces the same `item_code` multiple times with slightly different metadata (different PO batches), confusing users and risking accidental re-selection.
- Historical costing per batch is scattered across many `Stock` entries; aggregations require careful joins and are prone to drift if a batch is deleted/recreated.
- Race conditions in delivery receipt processing previously created "ghost" stock entries (quantity/cost zero). While locks fix creation, the architecture still allows drift whenever a retry or manual PO edit recreates batches.

## Goals
1. Ensure exactly one canonical inventory record per SKU/`item_code` while retaining full traceability of individual receipts and consumptions.
2. Keep the system Xero-friendly: one `xero_id` per SKU, consistent Quantity-on-Hand, easy to send updates.
3. Improve UI/UX: ItemSelect lists distinct items without duplicates; users can view total quantity and drill down into batches when needed.
4. Preserve historical costing and audit trail (per receipt/batch) without polluting the primary stock table.
5. Eliminate duplicate `Stock` rows per PO line via constraints and data model changes.

## Proposed Target Model (High Level)
### Core entities
- **StockItem** (new): canonical record per SKU (`item_code`, `xero_id`, default metadata). Represents the consolidated view of an inventory item.
- **StockLot** (new): captures individual receipts/batches linked to a `StockItem`. Fields: `purchase_order_line`, `received_quantity`, `unit_cost`, `received_at`, `notes`, `source_job`, etc. This replaces the current `Stock` row per receipt.
- **StockTransaction** (optional/phase 3): ledger-style table for adjustments (receipts, consumptions, transfers). Lots become "receipts" in the log; consumptions create negative movements referencing a lot (FIFO/LIFO or explicit selection). This phase is optional if Phase 2 already delivers adequate traceability.

### Relationships
- `StockItem` 1-N `StockLot`; `StockLot` 1-N `StockTransaction` (if we introduce the ledger).
- Existing `CostLine` references adapt to point at `StockLot` (or `StockTransaction` when/if the ledger arrives).
- Xero sync reads `StockItem` for aggregate state, and can use `StockLot` for cost metadata when required.

## Incremental Implementation Plan
### Phase 0 - Hardening Current System
- Enforce delivery receipt row locks unconditionally.
- Add conditional `UniqueConstraint` on `Stock(source_purchase_order_line, is_active=True)`.
- Write data cleanup script:
  - Identify duplicate active stocks per PO line or per `xero_id`.
  - Migrate quantity/cost to the intended record; deactivate or archive the ghost; clear duplicate `xero_id`.
  - Produce a report for manual reconciliation (dates, job references, delta quantities).

### Phase 1 - Introduce Canonical StockItem
- Create new `StockItem` model populated from distinct `item_code` / `xero_id` pairs.
- Backfill existing `Stock` rows to link to their `StockItem`.
- Migrate Xero sync to operate via `StockItem` for item metadata (while still updating `Stock` for quantity until Phase 2).
- Adjust ItemSelect API/UI to list `StockItem` entries with aggregated quantity/cost (sum of linked `Stock`).

### Phase 2 - Split Stock into Item vs Lot
- Introduce `StockLot` table mirroring the current `Stock` schema plus FK to `StockItem`.
- Create migration that copies each existing `Stock` row into `StockLot`, update foreign keys from cost lines, purchase order allocation views, etc.
- Update delivery receipt flow:
  - Instead of deleting `Stock`, delete `StockLot` for that PO line (UniqueConstraint ensures only one active lot per line).
  - Recreate `StockLot` with receipt data, link to `StockItem` (lookup by `item_code` / create new mapping via parsing).
  - Update `StockItem` aggregate fields (quantity on hand) atomically (annotated queries or stored totals).
- Update stock consumption services to decrement `StockLot` quantities or create ledger entries if we proceed with Phase 3.

### Phase 3 - Ledger / Movements (optional)
- Add `StockTransaction` model: `{stock_item, lot, quantity_delta, reference (cost line/job), timestamp, notes}`.
- Replace direct `StockLot.quantity` updates with transaction entries + derived totals (like a ledger) if Phase 2 proves insufficient for auditability.
- Provide APIs for viewing the ledger, running FIFO/LIFO, performing adjustments.

#### Phase 3 Trade-offs
- **Pros**
  - Full audit trail of every movement; easier to support FIFO/LIFO or WIP adjustments.
  - Simplifies reconciliation when multiple systems (delivery receipts, jobs, Xero) manipulate stock.
- **Cons**
  - Increased modelling and migration complexity (new table, more writes per operation).
  - Requires frontend/UX changes to expose or hide ledger detail appropriately.
  - Might be overkill if Phase 2 already satisfies reporting and traceability needs.

### Phase 4 - Decommission Legacy Stock Table
- Once `StockLot` fully adopts responsibilities, drop legacy columns/model, rename `StockLot` to `Stock` (or keep new naming if clearer).
- Update documentation, tests, scripts accordingly.

## Frontend & API Impacts
- ItemSelect endpoints need to fetch `StockItem` with aggregate quantities, latest cost, and optionally a breakdown of lots.
- PO UI may surface both consolidated view (quantity available) and lot drill-down.
- Need to coordinate ETag support for PO updates (already documented) to ensure concurrent edits fail fast.

## Data Migration Considerations
- Backfill scripts must be idempotent and safe for large datasets.
- Provide reconciliation reports pre/post migration to validate totals per SKU.

## Xero Integration Strategy
- During transition, keep `StockItem` and `StockLot` in sync with Xero expectations:
  - Map `StockItem` <-> Xero Item (1:1).
  - `StockLot` influences quantity and cost; ensure we send aggregate quantity so Xero QOH remains accurate.
  - Reconcile historical `raw_json` data (currently stored per `Stock`) -- decide to keep per lot or move to a `StockItem` history table.

## Risks & Open Questions
- How to handle price variance between lots of the same SKU? Need policy for presenting "latest cost" vs average vs lot-level.
- Consumption logic: do downstream services need to pick a specific lot or can they consume aggregated quantity? Implementation complexity vs business expectations.
- Performance: recalculating aggregates in real time vs maintaining denormalized totals.
- Testing strategy: integration tests for delivery receipt -> stock -> Xero sync, ensuring duplicates never reappear.
- Should we stop at `StockItem` + `StockLot` or invest in a `StockTransaction` ledger? Revisit after Phase 2.
