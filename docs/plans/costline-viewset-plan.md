# CostLine/CostSet ViewSet Refactoring Plan

## Current State
CostLine and CostSet use APIView classes in `apps/job/views.py`:
- `CostLineAPIView` - handles list/create at `/jobs/rest/<job_id>/costsets/<costset_id>/lines/`
- `CostLineDetailAPIView` - handles retrieve/update/delete at `.../lines/<line_id>/`
- `CostSetAPIView` - handles list/create at `/jobs/rest/<job_id>/costsets/`
- `CostSetDetailAPIView` - handles retrieve/update/delete at `.../costsets/<costset_id>/`

## Proposed Changes

### 1. CostSetViewSet
Convert to `ModelViewSet` with:
- Nested under Job (filter by job_id from URL)
- Standard CRUD operations
- Soft delete pattern

### 2. CostLineViewSet
Convert to `ModelViewSet` with:
- Nested under CostSet (filter by costset_id from URL)
- Standard CRUD operations
- Preserve business logic for different kinds (time, material, adjustment)
- Preserve validation patterns

## Complexity Factors
1. **Nested Resources**: CostLines are within CostSets within Jobs
2. **Business Logic**: Different handling for time/material/adjustment kinds
3. **Existing Patterns**: Complex validation and authorization

## Implementation Steps
- [ ] Create CostSetViewSet in new file
- [ ] Create CostLineViewSet in new file
- [ ] Update URL patterns to use nested routers (drf-nested-routers)
- [ ] Remove old APIView classes
- [ ] Test all CRUD operations
- [ ] Regenerate schema.yml
