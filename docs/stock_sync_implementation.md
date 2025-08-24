# Bidirectional Stock Items Sync Implementation

## Problem Identified

The system only had unidirectional sync (Xero → Local) for stock items. Items created locally weren't synchronised back to Xero and didn't have valid `item_code` values, causing problems when creating Purchase Orders.

## Solution Implemented

### 1. New Sync Module (`apps/workflow/api/xero/stock_sync.py`)

**Main functions:**

- `generate_item_code(stock_item)`: Generates valid item codes based on metal_type, alloy and specifics
- `validate_stock_for_xero(stock_item)`: Validates if an item is ready for sync
- `sync_stock_to_xero(stock_item)`: Synchronises an individual item to Xero
- `sync_all_local_stock_to_xero(limit)`: Synchronises all local items without xero_id
- `update_stock_item_codes()`: Updates missing item_codes in existing items

**Item Code Generation:**
```python
# Examples of generated codes:
# Stainless Steel 304 → "SS-304-ROUNDBAR"
# Mild Steel Plate → "MS-10MMPLATE"
# Aluminium 6061 → "AL-6061T6-ANGLE"
# Generic Item → "STOCK-12345678"
```

### 2. Integration with Existing Services

**Updated:**
- `PurchasingRestService.create_stock()`: Generates item_code automatically
- `process_delivery_receipt()`: Generates item_code for PO stock
- `auto_parse_stock_item()`: Generates item_code after parsing

**All new stock items now receive valid item_codes automatically.**

### 3. Integration with Main Sync

The bidirectional sync has been integrated into the main Xero sync process:
- After synchronising items from Xero → Local
- Automatically synchronises items Local → Xero (limited to 50 at a time)
- Appears in the sync dashboard as "stock_local_to_xero"

### 4. Django Command for Management

**Command:** `python manage.py sync_stock_to_xero`

**Options:**
```bash
# Fix existing long codes (>30 chars)
python manage.py sync_stock_to_xero --fix-long-codes

# Only update missing codes
python manage.py sync_stock_to_xero --update-codes-only

# Synchronise all local items
python manage.py sync_stock_to_xero --sync-all

# Synchronise specific item
python manage.py sync_stock_to_xero --stock-id <uuid>

# View what would be done (dry run)
python manage.py sync_stock_to_xero --dry-run

# Limit number of items
python manage.py sync_stock_to_xero --limit 10
```

### 5. Test Script

**Script:** `scripts/test_stock_sync.py`

Tests:
- Item code generation for different material types
- Stock item validation
- Current sync statistics
- Examples with real data

## Files Modified

### New Files:
- `apps/workflow/api/xero/stock_sync.py` - Main sync module
- `apps/workflow/management/commands/sync_stock_to_xero.py` - Django command
- `scripts/test_stock_sync.py` - Test script

### Modified Files:
- `apps/workflow/api/xero/sync.py` - Integration with main sync + fixed validation error
- `apps/workflow/api/xero/__init__.py` - Function exports
- `apps/purchasing/services/purchasing_rest_service.py` - Auto-generation of codes
- `apps/purchasing/services/delivery_receipt_service.py` - Auto-generation of codes
- `apps/quoting/signals.py` - Auto-generation after parsing

## How to Use

### To Fix Existing Data:
```bash
# 1. Fix long item codes (>30 characters)
python manage.py sync_stock_to_xero --fix-long-codes

# 2. Update missing item_codes
python manage.py sync_stock_to_xero --update-codes-only

# 3. Synchronise items to Xero
python manage.py sync_stock_to_xero --sync-all
```

### For New Stock Items:
- **Automatic**: All new items receive item_codes automatically
- **Manual**: Use the command to synchronise specific items

### Monitoring:
- Detailed logs in `logs/xero_integration.log`
- Errors persisted in the `AppError` table
- Sync dashboard shows progress of "stock_local_to_xero"

## Benefits

1. **Truly Bidirectional Sync**: Local items are now sent to Xero
2. **Automatic Item Codes**: All new items receive valid codes
3. **PO Compatibility**: Purchase Orders now work correctly
4. **Flexible Management**: Commands for different sync scenarios
5. **Monitoring**: Logs and dashboard to track the process
6. **Data Correction**: Tools to fix existing data

## Fixes Implemented (v2)

### 🚨 **Problems Identified During Testing:**
1. **Item codes too long**: Codes like `stock-768bedb7-087c-43cb-92e7-4e4517144e5a` (44 characters) exceed Xero's 30-character limit
2. **Invalid account codes**: Codes 630 and 200 didn't exist in the Xero chart of accounts
3. **Missing prices**: Cost price and sales price weren't being included in Xero items
4. **Sync validation error**: Xero → Local sync failing on items without sales_details.unit_price

### ✅ **Corrections Applied:**

#### 1. **30-Character Limit**
- Item codes now strictly respect Xero's 30-character limit
- Smart truncation algorithm preserves important information
- Prefix "STK-" for generic items instead of "STOCK-"

#### 2. **Dynamic Account Codes**
- System now looks up valid accounts from Xero automatically
- Uses account codes 200 (Sales) and 300 (Purchases) when available
- Fallback to account type matching if specific codes don't exist

#### 3. **Price Integration**
- **Cost Price**: Uses `unit_cost` → PurchaseDetails.UnitPrice
- **Sales Price**: Uses `unit_revenue` → SalesDetails.UnitPrice
- Both prices now appear correctly in Xero

#### 4. **Validation Error Fix**
- Fixed rigid validation in Xero → Local sync
- Items without sales_details.unit_price now default to $0 instead of failing
- Sync continues without interruption

### 📊 **Examples of Fixed Item Codes**

- `stock-768bedb7-087c-43cb-92e7-4e4517144e5a` → `STK-768bedb7` (30 chars)
- `SS-304-VERYLONGSPECIFICATION` → `SS-304-VERYLONGSPEC` (30 chars)
- Generic codes: `STK-{8chars}` instead of `STOCK-{8chars}`

## Validation

The original error "local stock items don't have a valid item code" has been resolved:

✅ **Before**: Local stock items without item_code → PO creation failures
✅ **After**: Local stock items with valid item_code → POs work perfectly
✅ **Bidirectional Sync**: Local ↔ Xero working in both directions
✅ **Price Integration**: Cost and sales prices correctly synced to Xero
✅ **Error Handling**: Robust validation and error recovery
