# Product Mapping Backflow Plan

## Problem Statement

The product mapping validation system currently has a gap: when users validate and correct mappings in the ProductParsingMapping model, those corrections are not automatically synced back to the corresponding SupplierProduct records.

## Current Architecture Issues

1. **No Direct Relationship**: SupplierProduct has no hash field to reference ProductParsingMapping
2. **Dynamic Hash Lookup**: The system computes hashes on-the-fly to find related mappings
3. **One-Way Data Flow**: Initial parsing updates SupplierProduct.parsed_* fields, but validation corrections don't flow back
4. **Complex Lookup Logic**: Finding related SupplierProducts requires recomputing hashes

## Proposed Solution

### Add Explicit Hash Field to SupplierProduct

Add a `mapping_hash` field to SupplierProduct model that stores the SHA-256 hash of the product description. This creates an explicit relationship with ProductParsingMapping.

```python
class SupplierProduct(models.Model):
    # ... existing fields ...
    mapping_hash = models.CharField(max_length=64, blank=True, null=True, db_index=True)
```

### Update Validation Flow

Modify the `validate_mapping` view to update all related SupplierProduct records after validation:

```python
def validate_mapping(request):
    # ... existing validation logic ...

    # After saving validated mapping
    mapping.save()

    # Update all SupplierProducts using this mapping
    SupplierProduct.objects.filter(mapping_hash=mapping.input_hash).update(
        parsed_item_code=mapping.mapped_item_code,
        parsed_material_type=mapping.mapped_material_type,
        # ... other parsed fields ...
    )
```

## Implementation Steps

1. **✅ Add Migration**: Add `mapping_hash` field to SupplierProduct - COMPLETED
2. **✅ Populate Hash Values**: Create management command to populate existing records - COMPLETED
3. **✅ Update Signal Handler**: Ensure the hash is set when SupplierProduct is created/updated - COMPLETED
4. **✅ Modify Validation View**: Add backflow logic to update related SupplierProducts - COMPLETED
5. **✅ Test**: Verify validation corrections properly sync to all related products - COMPLETED
6. **⏳ Cleanup**: Delete the management command - PENDING (let populate_mapping_hashes finish first)

## Implementation Details

### Changes Made

**Database Schema:**
- Added `mapping_hash` CharField(64) with db_index=True to SupplierProduct model
- Migration `0011_add_mapping_hash_to_supplierproduct.py` created and applied

**Code Changes:**
- Created `apps/quoting/utils.py` with common hash calculation functions
- Updated `ProductParser._calculate_input_hash()` to use common function
- Updated signal handler in `apps/quoting/signals.py` to set mapping_hash on new records
- Modified validation view in `apps/purchasing/views/product_mapping.py` to update related SupplierProducts

**Hash Consistency:**
- Centralized hash calculation in `calculate_product_mapping_hash()` and `calculate_supplier_product_hash()`
- Ensures ProductParser and signal handler use identical logic
- Hash based on: `product_data.get('description', '') or product_data.get('product_name', '')`

## Benefits

- **Explicit Relationship**: Clear, indexed foreign key-like relationship
- **Simple Queries**: Easy to find all products using a specific mapping
- **Consistent Data**: Validation corrections automatically apply to all related products
- **Better Performance**: No need to compute hashes for lookups
- **Cleaner Code**: Removes complex dynamic hash computation logic

## Migration Considerations

Since the model isn't in production yet, this is a simple schema addition without complex data migration requirements.
