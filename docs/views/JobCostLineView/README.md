# Job Cost Line View Documentation

## Business Purpose
Provides REST API for managing individual cost line items within job cost sets in jobbing shop operations. Handles creation, updating, and deletion of cost lines for material, labor, and other expenses across estimate, quote, and actual costing phases. Essential for detailed job profitability tracking and accurate pricing throughout the quote → job → invoice workflow.

## Views

### CostLineCreateView
**File**: `apps/job/views/job_costline_views.py`
**Type**: Class-based view (APIView)
**URL**: `/job/rest/jobs/<uuid:job_id>/cost_sets/<str:kind>/cost_lines/`

#### What it does
- Creates new cost line items within specific job cost sets
- Supports different cost set types (estimate, quote, actual)
- Automatically creates cost sets if they don't exist
- Updates cost set summaries after cost line creation

#### Parameters
- `job_id`: UUID of job to add cost line to (path parameter)
- `kind`: Cost set type - "estimate", "quote", or "actual" (path parameter, defaults to "actual")
- JSON body with cost line data:
  - `description`: Cost line description (required)
  - `quantity`: Quantity/hours (required)
  - `unit_cost`: Cost per unit (required)
  - `unit_rev`: Revenue per unit (required)
  - `kind`: Cost line type (e.g., "time", "material")

#### Returns
- **201 Created**: Created cost line with full details
- **400 Bad Request**: Invalid kind parameter or validation errors
- **404 Not Found**: Job not found
- **500 Internal Server Error**: Creation failures or database errors

#### Integration
- Uses CostLineCreateUpdateSerializer for validation
- Automatically manages cost set creation and revision tracking
- Updates cost set summary with aggregated cost, revenue, and hours

### CostLineUpdateView
**File**: `apps/job/views/job_costline_views.py`
**Type**: Class-based view (APIView)
**URL**: `/job/rest/cost_lines/<int:cost_line_id>/`

#### What it does
- Updates existing cost line items with partial or complete data
- Recalculates cost set summaries after updates
- Maintains data integrity with transactional updates

#### Parameters
- `cost_line_id`: ID of cost line to update (path parameter)
- JSON body with updated cost line data (partial updates supported)

#### Returns
- **200 OK**: Updated cost line with full details
- **400 Bad Request**: Validation errors or invalid data
- **404 Not Found**: Cost line not found
- **500 Internal Server Error**: Update failures

#### Integration
- Uses CostLineCreateUpdateSerializer for validation
- Updates parent cost set summary automatically
- Supports partial updates for individual fields

### CostLineDeleteView
**File**: `apps/job/views/job_costline_views.py`
**Type**: Class-based view (APIView)
**URL**: `/job/rest/cost_lines/<int:cost_line_id>/`

#### What it does
- Permanently deletes cost line items from job cost sets
- Updates cost set summaries after deletion
- Maintains referential integrity

#### Parameters
- `cost_line_id`: ID of cost line to delete (path parameter)

#### Returns
- **204 No Content**: Successful deletion
- **404 Not Found**: Cost line not found
- **500 Internal Server Error**: Deletion failures

#### Integration
- Updates parent cost set summary after deletion
- Removes cost line contribution from aggregated totals
- Transaction-safe deletion with rollback capability

## Error Handling
- **400 Bad Request**: Invalid cost set kind, validation errors, or missing required fields
- **404 Not Found**: Job or cost line not found
- **500 Internal Server Error**: Database errors, transaction failures, or unexpected system errors
- Comprehensive logging for debugging and monitoring
- Transactional operations ensure data consistency

## Related Views
- Job costing views for cost set management
- Modern timesheet views for time entry cost lines
- Job management views for overall job profitability
- Purchasing views for material cost integration