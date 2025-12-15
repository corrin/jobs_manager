# PO Line Deletion Bug Investigation

**Date:** 2025-12-15
**Triggered by:** JO-0352 reported as "fully received but costs not on jobs"

## Action Required

### Bug #1: Frontend deletes PO lines instead of updating them
**File:** `apps/purchasing/services/purchasing_rest_service.py`
**Action:** Remove or block `_delete_lines()`. If frontend is sending `lines_to_delete`, that's a frontend bug - it should update lines in place.

### Bug #2: Xero sync uses description as unique key
**File:** `apps/workflow/api/xero/sync.py`
**Action:** Change `update_or_create` to use `xero_line_id` (from `line.line_item_id`) as the unique key, not `(supplier_item_code, description)`.

---

## Executive Summary

When PO lines are deleted and recreated (instead of updated in place), orphaned CostLines remain in the database. This results in:
1. Duplicate cost entries on jobs
2. Orphaned CostLines referencing non-existent PO lines
3. Potential double-counting of material costs

**Affected POs:** 3 (JO-0352, PO-0282, PO-0334)
**Total orphaned CostLines:** 11

## Root Cause

### The Bug Flow

```
1. PO created with lines (line IDs: A, B, C)
2. Delivery processed → CostLines created referencing line IDs A, B, C
3. User edits PO → Frontend sends delete(A,B,C) + create(D,E,F)
4. Old lines deleted, NEW line IDs generated (D, E, F)
5. Delivery processed again → CostLines created referencing D, E, F
6. Result: 6 CostLines exist, 3 are orphaned (reference deleted A, B, C)
```

### Code Location

**File:** `apps/purchasing/services/purchasing_rest_service.py`

```python
# Lines 66-72 - No cleanup of related records
@staticmethod
def _delete_lines(lines_to_delete: list[str], po: PurchaseOrder) -> None:
    for line_id in lines_to_delete:
        try:
            line = PurchaseOrderLine.objects.get(id=line_id, purchase_order=po)
            line.delete()  # ← Deletes line but NOT related CostLines/Stock
        except PurchaseOrderLine.DoesNotExist:
            continue
```

### Why Lines Are Deleted Instead of Updated

The frontend appears to send PO edits as `lines_to_delete` + new `lines` when:
- Description changes significantly
- Job assignment changes
- User removes and re-adds a line

The `_process_line` function (line 122) checks if line ID exists:
- If ID exists → update in place
- If ID missing/new → create new line

If frontend doesn't preserve line IDs during edits, new lines are created.

## Affected Data

### JO-0352 (Steelmasters Auckland Limited)

| Status | Description | Cost | Qty | Job | Issue |
|--------|-------------|------|-----|-----|-------|
| ORPHAN | M16 X 35 (OR 40MM) STEEL CAP SCREWS | $0.00 | 8 | 95427 | $0 placeholder |
| ORPHAN | M6 X 50 ZINC PLATED | $0.00 | 30 | 96262 | $0 placeholder |
| ORPHAN | M6 NYLOC NUTS ZINC PLATED | $0.00 | 30 | 96262 | $0 placeholder |
| ORPHAN | M6 CSK SOCKET SCREWS 304 STAINLESS STEEL | $0.00 | 30 | 96450 | $0 placeholder |
| Valid | M16 X 35 BLACK SOCKET HEAD CAPSCREW | $1.34 | 8 | 95427 | ✓ |
| Valid | M6 X 50 ZINC CL 8.8 HT HEX SETSCREW | $0.37 | 30 | 96262 | ✓ |
| Valid | M6 X 20 G304 STAINLESS CSK SOCKET SCREW | $0.40 | 30 | 96262 | ✓ |
| Valid | M6 ZINC DIN 985 NYLOC NUT | $0.05 | 30 | 96450 | ✓ |

**Timeline:**
- Dec 10, 21:24 - PO created
- Dec 12, 02:50 - First delivery → CostLines with $0 (prices TBC)
- Dec 12-14 - Lines edited (deleted + recreated with actual prices)
- Dec 14, 21:07 - Second delivery → CostLines with actual costs

### PO-0282 (Status: draft)

| Status | Description | Cost | Qty | Job |
|--------|-------------|------|-----|-----|
| ORPHAN | 95761 - 0.95mm Galvanised Z275 | $48.53 | 4 | 95761 |
| ORPHAN | FREIGHT - COURIER CHARGEJN5761 | $30.00 | 1 | 95761 |
| ORPHAN | 95761 - 1.55mm Galvanised Z275 | $98.11 | 2 | 95761 |
| ORPHAN | JN96171 - freight | $30.00 | 1 | 96171 |
| ORPHAN | 50mm x 8mm Flat Bar G300 | $58.24 | 1 | 96171 |
| Valid | (5 lines with similar items) | various | various | 96072/96171 |

**Note:** Orphans have REAL costs, not just $0 placeholders.

### PO-0334 (Status: submitted)

| Status | Description | Cost | Qty | Job |
|--------|-------------|------|-----|-----|
| ORPHAN | 96257 - M8 ZINC CLASS 8 HEX NUT | $0.11 | 50 | 96257 |
| ORPHAN | STOCK - M8 ZINC CLASS 8 HEX NUT | $0.11 | 100 | 95427 |
| Valid | M8 ZINC CLASS 8 HEX NUT | $0.11 | 50 | 96268 |
| Valid | M8 ZINC CLASS 8 HEX NUT | $0.11 | 50 | 96257 |
| Valid | M8 ZINC CLASS 8 HEX NUT | $0.11 | 100 | 95427 |

## Required Fixes

### Fix #1: Remove PO Line Deletion from API

Remove `lines_to_delete` from the API contract entirely.

**File:** `apps/purchasing/serializers.py`

```python
# REMOVE these lines (221-226):
lines_to_delete = serializers.ListField(
    child=serializers.UUIDField(),
    required=False,
    allow_empty=True,
    help_text="List of line IDs to delete",
)
```

**File:** `apps/purchasing/services/purchasing_rest_service.py`

```python
# REMOVE _delete_lines() method entirely (lines 66-72)

# REMOVE these lines from update_purchase_order() (lines 326-328):
lines_to_delete = data.get("lines_to_delete")
if lines_to_delete:
    PurchasingRestService._delete_lines(lines_to_delete, po)
```

If frontend is using `lines_to_delete`, it will get an API error, surfacing the frontend bug.

### Fix #2: Xero Sync - Use line_item_id as Unique Key

**File:** `apps/workflow/api/xero/sync.py`

1. Add migration to add `xero_line_id` field to `PurchaseOrderLine`:

```python
# New field
xero_line_id = models.CharField(max_length=50, null=True, blank=True, db_index=True)
```

2. Change `update_or_create` in `transform_purchase_order()`:

```python
# BEFORE (buggy - description changes create new lines):
PurchaseOrderLine.objects.update_or_create(
    purchase_order=po,
    supplier_item_code=line.item_code or "",
    description=description,
    defaults={...}
)

# AFTER (correct - xero_line_id is stable):
PurchaseOrderLine.objects.update_or_create(
    purchase_order=po,
    xero_line_id=line.line_item_id,
    defaults={
        "description": description,
        "supplier_item_code": line.item_code or "",
        "quantity": quantity,
        "unit_cost": getattr(line, "unit_amount", None),
    }
)
```

### Fix #3: Validate Prices Before Delivery (Secondary)

**File:** `apps/purchasing/services/delivery_receipt_service.py`

Add validation to prevent $0 cost deliveries:

```python
# In _validate_and_prepare_allocations()
if line.unit_cost is None or line.unit_cost <= 0:
    raise DeliveryReceiptValidationError(
        f"Cannot process delivery for line '{line.description}': "
        f"price not confirmed (${line.unit_cost})"
    )
```

## Immediate Data Fix

Delete the 11 orphaned CostLines:

```python
from apps.job.models import CostLine

orphan_ids = [
    # JO-0352
    '0bd15779-f076-4036-ac81-8e7c6263992d',
    '4a3ce0db-e2b5-44a9-9852-f07677c94c3a',
    '52479f19-ac36-4054-ad4a-d055519ddfe0',
    'ae47c6ae-5cfb-4a43-a8a0-a7b62ae3114d',
    # PO-0282 - CAUTION: these have real costs!
    # PO-0334 - CAUTION: these have real costs!
]

# Only safe to delete JO-0352 orphans ($0 cost)
CostLine.objects.filter(id__in=orphan_ids[:4]).delete()

# For PO-0282 and PO-0334, manual review needed to determine
# if orphans represent real costs that should be preserved
```

## Questions for Business (Data Cleanup)

1. **PO-0282 orphans:** These have real costs ($48.53, $98.11, etc.) on Job 95761. Are these legitimate costs that should remain, or duplicates that should be deleted?

2. **PO-0334 orphans:** These have costs on Jobs 96257 and 95427. Are the valid CostLines the correct ones, or are the orphans the real deliveries?

## Files to Change

| File | Change |
|------|--------|
| `apps/purchasing/serializers.py` | Remove `lines_to_delete` field |
| `apps/purchasing/services/purchasing_rest_service.py` | Remove `_delete_lines()` and its call |
| `apps/purchasing/models.py` | Add `xero_line_id` field to PurchaseOrderLine |
| `apps/workflow/api/xero/sync.py` | Use `xero_line_id` as unique key |
| `apps/purchasing/services/delivery_receipt_service.py` | Add $0 price validation (optional) |

## Related Code Paths

- `apps/purchasing/services/purchasing_rest_service.py` - `_delete_lines()` (TO BE REMOVED), `update_purchase_order()`
- `apps/purchasing/services/delivery_receipt_service.py` - `process_delivery_receipt()`, `_create_costline_from_allocation()`
- `apps/purchasing/serializers.py` - `PurchaseOrderUpdateSerializer` with `lines_to_delete` (TO BE REMOVED)
- `apps/workflow/api/xero/sync.py` - `transform_purchase_order()` (TO BE FIXED)
