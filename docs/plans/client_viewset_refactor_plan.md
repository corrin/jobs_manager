# Client ViewSet Refactoring Plan

## Approach

**Breaking change refactor** - No backwards compatibility. Fix all coding guideline violations:
1. **Eliminate service layer** - Move Xero logic to Xero adapter
2. **Remove backend formatting** - Return raw data, frontend formats for display
3. **Use ModelViewSet** - Follow `ClientContactViewSet` pattern
4. **Testable incrementally** - Each commit should leave the app functional

## Coding Guideline Violations to Fix

1. **Service layer doing too much** - `ClientRestService` has formatting, queries, AND Xero calls mixed together
2. **Backend formatting** - `"$1,234.56"` strings should be raw `Decimal`
3. **Verbose APIViews** - Should be a single `ModelViewSet`
4. **Manual schema decorators** - Should auto-generate from serializer

## Where Should Xero Logic Go?

**Decision: Xero adapter (hexagonal architecture)**
- `apps/workflow/api/xero/client_sync.py`
- Already have similar patterns: `XeroPurchaseOrderManager`, `sync_clients()`
- ViewSet calls adapter methods
- Pros: Clean separation, follows existing Xero patterns

## Implementation Steps (Incremental, Testable)

### Step 1: Refactor service layer - add raw data methods alongside formatted
- Add `_format_client_summary_raw()` alongside `_format_client_summary()`
- Add `_format_client_detail_raw()` alongside `_format_client_detail()`
- Mark old formatted methods as DEPRECATED
- **Test:** App still works with existing formatted responses

### Step 2: Create Xero adapter for client sync
- Create `apps/workflow/api/xero/client_sync.py`
- Move `_create_client_in_xero()` from service to adapter as `create_client_in_xero()`
- Move `_update_client_in_xero()` from service to adapter as `update_client_in_xero()`
- Update service layer to call adapter instead of internal methods
- **Test:** Create and update clients still work with Xero sync

### Step 3: Create ClientViewSet with basic CRUD
- Create `apps/client/views/client_viewset.py`
- Implement list, retrieve using raw data serializers
- ViewSet.perform_create() calls Xero adapter
- ViewSet.perform_update() calls Xero adapter
- Update `urls_rest.py` to use router for new ViewSet
- **Test:** New endpoints work alongside old ones

### Step 4: Add custom actions to ViewSet
- `@action search` - client search (uses raw data)
- `@action jobs` - client's jobs list
- **Test:** Search and jobs endpoints work on new ViewSet

### Step 5: Update frontend to use raw data
- Document API changes for frontend team
- Frontend formats `total_spend` as currency
- Frontend formats `last_invoice_date` for display
- **Test:** Frontend displays data correctly

### Step 6: Switch URLs to new ViewSet
- Update `urls_rest.py` to route all client endpoints through ViewSet
- Remove old APIView routes
- **Test:** All endpoints work through ViewSet

### Step 7: Cleanup
- Delete `client_rest_views.py` (should be empty)
- Delete `ClientRestService` (should be empty)
- Remove unused serializers
- Remove deprecated formatted methods
- **Test:** Full regression test

## URL Changes

| Old URL | New URL | Method |
|---------|---------|--------|
| `/clients/all/` | `/clients/` | GET |
| `/clients/create/` | `/clients/` | POST |
| `/clients/<id>/` | `/clients/<id>/` | GET |
| `/clients/<id>/update/` | `/clients/<id>/` | PUT/PATCH |
| `/clients/search/` | `/clients/search/` | GET |
| `/clients/<id>/jobs/` | `/clients/<id>/jobs/` | GET |

## Response Format Changes

| Field | Old | New |
|-------|-----|-----|
| `total_spend` | `"$1,234.56"` | `1234.56` |
| `last_invoice_date` | string | ISO datetime |
| UUIDs | string | string (unchanged) |

## Files to Modify

1. `apps/client/services/client_rest_service.py` - Add raw methods, mark formatted as deprecated
2. `apps/workflow/api/xero/client_sync.py` - **CREATE** Xero adapter
3. `apps/client/views/client_viewset.py` - **CREATE** new ViewSet
4. `apps/client/serializers.py` - Fix formatting, use field lists
5. `apps/client/urls_rest.py` - Update routing
6. `apps/client/views/client_rest_views.py` - **DELETE** entirely (after migration)

## Success Criteria

- [ ] Single `ClientViewSet` handles all Client CRUD
- [ ] No `@extend_schema` decorators needed for basic CRUD
- [ ] Service layer eliminated
- [ ] Raw data returned (no backend formatting)
- [ ] Xero integration works via adapter
- [ ] All tests pass
- [ ] App testable after each commit
