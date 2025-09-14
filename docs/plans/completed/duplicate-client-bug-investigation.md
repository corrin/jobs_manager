# Duplicate Client Bug Investigation

## ✅ RESOLVED - 2025-08-11

**Problem:** After restore process, found 27 duplicate client names (54 total records).

## What We Fixed:

- ✅ Fixed `sync_clients()` logic in `apps/workflow/api/xero/sync.py:548-610`
- ✅ Updated backup-restore process steps
- ✅ Fixed EstimateAmount validation in `sync.py:1206-1208` (only send if > 0)
- ✅ Made `--clear-xero-ids` optional in `seed_xero_from_database` command

## Testing Results - 2025-08-11:

- ✅ No duplicates in production data (Step 8)
- ✅ No duplicates after migrations (Step 9)
- ✅ No duplicates after fixtures (Step 10)
- ✅ **NO duplicates created after Xero sync (Step 20)** - FIXED!

## Verification:

```sql
-- Confirmed zero duplicate client names after full restore + sync:
SELECT name, COUNT(*) as duplicate_count
FROM workflow_client
GROUP BY name
HAVING COUNT(*) > 1;
-- Result: 0 rows (no duplicates)

-- Final client counts:
-- Total: 3883 clients
-- Linked to Xero: 593 clients
-- Unlinked: 3290 clients
```

## Root Cause (Historical):

The sync logic didn't properly handle the case where multiple Xero contacts existed with the same name as existing clients, causing duplicate creation instead of proper linking.

## Resolution:

Enhanced `sync_clients()` to prevent duplicate creation by properly checking for name conflicts before creating new client records.

**Status: COMPLETED** - Bug resolved and verified through full restore process.
