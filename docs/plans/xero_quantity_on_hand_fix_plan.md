# Xero Sync `quantity_on_hand` Field Error Fix Plan

## Problem Statement

The Xero sync process fails with the error "Missing fields ['quantity_on_hand'] for item 75189459-e8ad-4007-bec3-10044e673996" when attempting to sync inventory items from Xero. 

**Root Cause**: The `transform_stock()` function in the Xero sync code requires the `quantity_on_hand` field for all items, but Xero omits this field entirely for untracked inventory items. When an item is marked as "untracked" in Xero (Track inventory checkbox is unchecked), the `quantity_on_hand` field is not included in the API response.

## Current Architecture Issues

1. **Strict Field Validation**: The `validate_required_fields()` function treats `quantity_on_hand` as always required
2. **Missing Tracking Status**: No field in the Stock model to record whether an item is inventory-tracked in Xero
3. **Silent Data Loss Risk**: Previous attempts to fix this might have silently converted untracked items to tracked by setting quantity to 0
4. **API Response Variation**: Xero's API behaves differently for tracked vs untracked items

## Xero API Behavior (UPDATED with Real Data)

**Research Finding**: Analysis of actual Xero raw_json data reveals:

- **Tracked Items**: Have `"_is_tracked_as_inventory": true` and numeric `"_quantity_on_hand"` value
- **Untracked Items**: Have `"_is_tracked_as_inventory": false` and `"_quantity_on_hand": null`
- **Key Insight**: The `quantity_on_hand` field IS present for both types, but `null` for untracked items
- **Authoritative Field**: `is_tracked_as_inventory` is the definitive indicator of tracking status

**Corrected Approach**: Use `is_tracked_as_inventory` field instead of checking field presence.

## Proposed Solution

### 1. Add Inventory Tracking Status Field

Add a `xero_inventory_tracked` boolean field to the Stock model to preserve Xero's tracking status:

```python
class Stock(models.Model):
    # ... existing fields ...
    xero_inventory_tracked = models.BooleanField(
        default=False, 
        help_text="Whether this item is inventory-tracked in Xero"
    )
```

### 2. Update Sync Logic

Modify `transform_stock()` function to detect and handle tracked vs untracked items:

```python
def transform_stock(xero_item, xero_id):
    # Get basic required fields - NO FALLBACKS, fail early if missing
    item_code = getattr(xero_item, "code", None)
    description = getattr(xero_item, "name", None)
    is_tracked = getattr(xero_item, "is_tracked_as_inventory", None)
    xero_last_modified = getattr(xero_item, "updated_date_utc", None)
    
    # Base validation requirements (always required)
    required_fields = {
        "code": item_code,
        "name": description,
        "is_tracked_as_inventory": is_tracked,
        "updated_date_utc": xero_last_modified,
    }
    
    # Only access and validate quantity_on_hand for tracked items
    if is_tracked:
        quantity = getattr(xero_item, "quantity_on_hand", None)
        required_fields["quantity_on_hand"] = quantity
        quantity_value = Decimal(str(quantity))
    else:
        # For untracked items, don't access quantity_on_hand at all
        quantity_value = Decimal("0")
    
    validate_required_fields(required_fields, "item", xero_id)
    
    # Set appropriate values based on tracking status
    defaults = {
        # ... other fields ...
        "xero_inventory_tracked": is_tracked,
        "quantity": quantity_value,
    }
```

### 3. Preserve Data Integrity

- **Don't convert untracked to tracked**: Maintain clear distinction
- **Set appropriate defaults**: Use `quantity=0` for untracked items (reasonable default)
- **Log status changes**: When items change tracking status between syncs

## Implementation Steps

1. **📝 Write Plan**: Document the complete solution approach - ✅ COMPLETED
2. **🔧 Add Database Field**: Add `xero_inventory_tracked` to Stock model - ✅ COMPLETED
3. **📦 Create Migration**: Generate Django migration for the new field - ✅ COMPLETED
4. **⚙️ Update Sync Logic**: Modify `transform_stock()` to handle both item types - ✅ COMPLETED
5. **🧪 Test Changes**: Verify with both tracked and untracked items - ✅ COMPLETED
6. **🚀 Deploy**: Apply migration and deploy updated sync logic - ✅ COMPLETED

## Implementation Details

### Database Schema Changes

**Stock Model Addition:**
```python
xero_inventory_tracked = models.BooleanField(
    default=False,
    help_text="Whether this item is inventory-tracked in Xero (has quantity_on_hand field)"
)
```

**Migration Considerations:**
- Default `False` for existing records (safe assumption)
- Add database index if frequently queried
- Consider data migration to set correct values for existing Xero items

### Code Changes Required

**File: `/home/corrin/src/jobs_manager/apps/purchasing/models.py`**
- Add `xero_inventory_tracked` field to Stock model

**File: `/home/corrin/src/jobs_manager/apps/workflow/api/xero/sync.py`**
- Update `transform_stock()` function around lines 330-340
- Modify validation logic to conditionally require `quantity_on_hand`
- Set `xero_inventory_tracked` based on field presence

### Validation Logic Changes

**Before (Current - Broken):**
```python
validate_required_fields(
    {
        "code": item_code,
        "name": description,
        "quantity_on_hand": quantity,  # Always required - BREAKS for untracked items
        "updated_date_utc": xero_last_modified,
    },
    "item",
    xero_id,
)
```

**After (Fixed):**
```python
# Get basic required fields - NO FALLBACKS, fail early if missing
item_code = getattr(xero_item, "code", None)
description = getattr(xero_item, "name", None)
is_tracked = getattr(xero_item, "is_tracked_as_inventory", None)
xero_last_modified = getattr(xero_item, "updated_date_utc", None)

# Base validation requirements (always required)
required_fields = {
    "code": item_code,
    "name": description,
    "is_tracked_as_inventory": is_tracked,
    "updated_date_utc": xero_last_modified,
}

# Only access and validate quantity_on_hand for tracked items
if is_tracked:
    quantity = getattr(xero_item, "quantity_on_hand", None)
    required_fields["quantity_on_hand"] = quantity

validate_required_fields(required_fields, "item", xero_id)
```

## Benefits

- **✅ Fixes Sync Errors**: Untracked items will no longer cause sync failures
- **✅ Preserves Data Integrity**: Maintains distinction between tracked/untracked items  
- **✅ Prevents Silent Conversion**: Won't accidentally mark untracked items as tracked
- **✅ Future-Proof**: Handles Xero API variations correctly
- **✅ Audit Trail**: Clear record of tracking status for each item

## Risk Mitigation

- **Database Migration**: Low risk, adding non-critical boolean field
- **Sync Logic Changes**: Defensive programming - handles both item types safely
- **Default Values**: Conservative approach (quantity=0 for untracked items)
- **Backward Compatibility**: Existing tracked items continue working unchanged

## Testing Strategy

1. **Unit Tests**: Test `transform_stock()` with both tracked and untracked mock items
2. **Integration Tests**: Sync real Xero data including both item types
3. **Migration Test**: Verify migration applies cleanly to existing data
4. **Validation**: Confirm untracked items sync without errors

## Error Context

**Original Error**: `Missing fields ['quantity_on_hand'] for item 75189459-e8ad-4007-bec3-10044e673996`

**Error Location**: `/home/corrin/src/jobs_manager/apps/workflow/api/xero/sync.py:334` in `validate_required_fields()` call

**Affected Items**: Any Xero inventory item with "Track inventory" checkbox unchecked

## Related Documentation

- **Xero API Docs**: Items endpoint behavior for tracked vs untracked inventory
- **Django Migrations**: Standard migration process for adding model fields
- **CLAUDE.md**: Follow defensive programming principles - "FAIL EARLY" but handle expected API variations

## Success Criteria

- ✅ Xero sync completes without `quantity_on_hand` errors
- ✅ Both tracked and untracked items sync correctly
- ✅ Stock model accurately reflects Xero tracking status
- ✅ No data integrity issues introduced
- ✅ Existing tracked items continue working unchanged