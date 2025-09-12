# Job Costing View Documentation

## Business Purpose
Provides REST API access to job costing data for profitability tracking in jobbing shop operations. Enables retrieval of estimate, quote, and actual cost sets for individual jobs, supporting the financial analysis and project management across the quote → job → invoice workflow.

## Views

### JobCostSetView
**File**: `apps/job/views/job_costing_views.py`
**Type**: Class-based view (APIView with JobLookupMixin)
**URL**: `/jobs/rest/jobs/<uuid:pk>/cost_sets/<str:kind>/`

#### What it does
- Retrieves the latest CostSet for a specific job and cost type
- Provides access to estimate, quote, and actual costing data
- Critical for project profitability tracking and financial analysis
- Supports cost comparison across different project phases

#### Parameters
- `pk`: Job primary key (UUID)
- `kind`: CostSet type - must be one of:
  - `estimate`: Initial cost estimation
  - `quote`: Quoted pricing for customer
  - `actual`: Real costs incurred during job execution

#### Returns
- **200 OK**: Serialized CostSet data including cost lines and summary
- **400 Bad Request**: Invalid kind parameter
- **404 Not Found**: Job not found or no cost set of specified kind exists

#### Integration
- Uses JobLookupMixin for job retrieval and error handling
- Integrates with CostSet model for versioned costing data
- Uses CostSetSerializer for consistent API response format
- No direct Xero integration (internal costing system)

## Error Handling
- **400 Bad Request**: Invalid kind parameter (not estimate/quote/actual)
- **404 Not Found**: Job with specified ID does not exist or no cost set found
- Comprehensive logging for debugging costing data retrieval issues
- Legacy error format support for consistent API responses

## Related Views
- CostLineCreateView, CostLineUpdateView, CostLineDeleteView for cost line management
- Job management views for associated job context
- Modern timesheet views for actual cost tracking
- KPI views for profitability analysis using costing data
