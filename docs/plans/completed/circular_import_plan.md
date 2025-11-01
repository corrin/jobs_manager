# Circular Import Elimination Plan

## Problem Statement

Django project has deep circular import issues where modules import models at module level, causing `AppRegistryNotReady` errors during Django setup. This prevents URL documentation generation and potentially other Django operations.

## Root Cause Analysis

Files importing models at module level trigger model loading during Django app initialization, before the app registry is ready. This creates a circular dependency.

## Assessment Results

### High Risk Files (Imported in **init**.py - BREAKS DJANGO STARTUP)

These files are imported by **init**.py files and cause immediate startup failure:

1. **apps/workflow/authentication.py** ✅ FIXED

   - Fixed: Moved `ServiceAPIKey` import inside methods

2. **apps/workflow/xero_webhooks.py** ❌ HIGH PRIORITY

   - Imports: `CompanyDefaults` at module level
   - Imported by: `apps/workflow/__init__.py`

3. **apps/accounting/services.py** ❌ HIGH PRIORITY
   - Imports: `Staff`, `Client`, `Job`, `CompanyDefaults` at module level
   - Imported by: `apps/accounting/__init__.py` (but we excluded services from auto-generation)

### Medium Risk Files (Imported by High Risk Files)

These are imported by the high-risk files and could cause cascading failures:

4. **apps/workflow/api/xero/reprocess_xero.py** ❌ MEDIUM PRIORITY

   - Imports: Multiple models at module level
   - Imported by: workflow API init files

5. **apps/workflow/api/xero/sync.py** ❌ MEDIUM PRIORITY
   - Imports: Multiple models at module level

### Low Risk Files (Only imported when used)

These don't break startup but should be fixed for code quality:

- All view files, serializers, forms, admin files (60+ files)
- Management commands
- Services not imported in **init**.py

## Execution Plan

### Phase 1: Fix High Priority (Required for Django startup)

1. ✅ **apps/workflow/authentication.py** - COMPLETED
2. **apps/workflow/xero_webhooks.py** - Move `CompanyDefaults` import inside functions
3. Test Django setup after each fix

### Phase 2: Verify Django Setup Works

1. Test: `python -c "import django; django.setup()"`
2. Test: `python scripts/generate_url_docs.py --help`
3. Add URL docs back to pre-commit if working

### Phase 3: Fix Medium Priority (Cascade prevention)

1. Fix workflow API files
2. Fix any remaining high-risk files discovered during testing

### Phase 4: Low Priority Cleanup (Code quality)

1. Fix remaining view files, serializers, etc.
2. This is optional - won't break functionality

## Current Status

- ✅ authentication.py fixed
- ❌ Django setup still fails on xero_webhooks.py
- ❌ URL docs script still fails

## Next Action

Fix `apps/workflow/xero_webhooks.py` by moving `CompanyDefaults` import inside function.
