# Duplicate Client Bug Investigation

## Current Status - 2025-08-10

**Problem:** After restore process, found 27 duplicate client names (54 total records).

**What We Fixed:**
- ✅ Fixed `sync_clients()` logic in `apps/workflow/api/xero/sync.py`
- ✅ Updated backup-restore process steps
- ✅ Tested - sync logic works correctly, no new duplicates created

**What We Know:**
- ✅ No duplicates in production data (Step 8)
- ✅ No duplicates after migrations (Step 9)
- ✅ No duplicates after fixtures (Step 10)
- ❌ 27 duplicates found after Xero sync (Step 20)

**Conclusion:** The duplicates are created during Xero sync despite our fixes.

## Root Cause

The issue is that **Xero Demo Company has multiple contacts with the same names as our production clients**.

Example with Hamilton Group:
1. Our production client "Hamilton Group" exists (no xero_contact_id)
2. Xero Demo Company has TWO contacts named "Hamilton Group"
3. First Xero contact links to our existing client ✅
4. Second Xero contact creates a NEW client record ❌

## Next Session

**Options:**
1. **Accept this behavior** - Demo company duplicates are expected
2. **Enhance logic** - Skip Xero contacts that would create name conflicts
3. **Use different Xero tenant** - One without conflicting names
