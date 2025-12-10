# Job Status Field Naming Consistency Refactor

## Problem Summary

The backend uses inconsistent field names for job status across different API endpoints:

| Serializer | Field Name | Endpoint Type |
|------------|------------|---------------|
| JobSerializer | `job_status` | Main job detail API |
| CompleteJobSerializer | `job_status` | Archive jobs list |
| JobPatchSerializer | `job_status` | Job updates (PATCH) |
| JobHeaderResponseSerializer | `status` | Header/quick load |
| WeeklyMetricsSerializer | `status` | Weekly metrics |
| KanbanJobSerializer | `status` + `status_key` | Kanban board |
| KanbanColumnJobSerializer | `status` + `status_key` | Kanban columns |
| JobStatusUpdateSerializer | `status` | Status change requests |

This inconsistency forces frontend consumers to implement translation layers with type assertions.

## Root Cause

The Job model uses `status` as the field name. Some serializers expose this directly (`status`), while others rename it to `job_status` via `source="status"` mapping to avoid ambiguity with other potential "status" fields in nested responses.

## Recommended Approach: Standardize on `status`

Use `status` consistently across all endpoints. This aligns with:
- The actual model field name
- REST conventions (shorter, clearer)
- The Kanban endpoints (already using `status`)

## Implementation Steps

### Step 1: Update JobSerializer
**File:** `apps/job/serializers/job_serializer.py`

Change line ~130:
```python
# FROM:
job_status = serializers.CharField(source="status")
# TO:
status = serializers.CharField()
```

Also update the `update()` method (~lines 305-306) to remove the special mapping:
```python
# REMOVE this mapping:
target_attr = "status" if attr == "job_status" else attr
```

**Test:** Run existing job detail API tests

---

### Step 2: Update CompleteJobSerializer
**File:** `apps/job/serializers/job_serializer.py`

Change line ~434:
```python
# FROM:
job_status = serializers.CharField(source="status")
# TO:
status = serializers.CharField()
```

**Test:** Run archive jobs tests

---

### Step 3: Update JobPatchSerializer
**File:** `apps/job/serializers/job_serializer.py`

Change line ~989:
```python
# FROM:
job_status = serializers.ChoiceField(choices=Job.JOB_STATUS_CHOICES, required=False)
# TO:
status = serializers.ChoiceField(choices=Job.JOB_STATUS_CHOICES, required=False)
```

**Test:** Run job PATCH tests

---

### Step 4: Update JobRestService Field Mapping
**File:** `apps/job/services/job_rest_service.py`

Remove the `job_status` mapping from `_FIELD_ATTRIBUTE_MAP` (~line 232):
```python
# REMOVE:
"job_status": "status",
```

Also update the comment at line ~781 and any undo description mappings.

**Test:** Run job update service tests

---

### Step 5: Update JobEvent Field Label Mappings
**File:** `apps/job/serializers/job_serializer.py`

Update the field label mappings (~lines 403, 931, 1376) that handle undo descriptions:
```python
# REMOVE the "job_status" entry, keep only "status":
"status": "status",
```

**Test:** Run job event/timeline tests

---

### Step 6: Update OpenAPI Documentation
**File:** Various serializer `help_text` and docstrings

Ensure all documentation refers to `status` consistently.

**Test:**
```bash
python manage.py spectacular --file /tmp/schema.yml
grep -E "(job_status|status)" /tmp/schema.yml | head -50
```

---

### Step 7: Frontend Coordination

The Vue.js frontend in `../jobs_manager_front/` will need corresponding updates.

**Frontend Workarounds to Remove After Backend Fix:**

| File | Line | Current Workaround |
|------|------|-------------------|
| `src/stores/jobs.ts` | 338 | `jobToHeader()` status conversion |
| `src/composables/useJobHeaderAutosave.ts` | 56-57 | `job_status` to `status` mapping |
| `src/views/JobView.vue` | 516 | `status` to `job_status` conversion |
| `src/components/timesheet/SummaryDrawer.vue` | 111 | `as any` cast with `job_status \|\| status` |

**Frontend Changes Required:**
1. Update TypeScript types to use `status` instead of `job_status`
2. Remove the translation/mapping logic listed above
3. Update API call sites to send/receive `status`
4. Remove any `as any` type assertions related to this inconsistency

This should be coordinated with the frontend team/Claude instance and deployed simultaneously with the backend changes.

---

## Files to Modify

| File | Changes |
|------|---------|
| `apps/job/serializers/job_serializer.py` | Lines ~130, ~305-306, ~434, ~989, ~403, ~931 |
| `apps/job/services/job_rest_service.py` | Lines ~232, ~781 |

## Testing Strategy

1. Run full test suite after each step:
   ```bash
   tox -e test -- apps/job/
   ```

2. Manual API verification:
   ```bash
   curl -X GET http://localhost:8000/api/rest/jobs/{job_number}/ | jq '.status'
   ```

3. OpenAPI schema validation:
   ```bash
   python manage.py spectacular --file /tmp/schema.yml --validate
   ```

## Breaking Change Notice

This is a **breaking API change** for any consumers using `job_status`. Ensure:
1. Frontend is updated simultaneously
2. Any external API consumers are notified
3. Consider a deprecation period with both fields if needed

## Current Status

- [ ] Step 1: Update JobSerializer
- [ ] Step 2: Update CompleteJobSerializer
- [ ] Step 3: Update JobPatchSerializer
- [ ] Step 4: Update JobRestService field mapping
- [ ] Step 5: Update JobEvent field label mappings
- [ ] Step 6: Update OpenAPI documentation
- [ ] Step 7: Frontend coordination (separate PR)
