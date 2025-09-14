# Month End REST View Documentation

## Business Purpose

Provides REST API endpoints for month-end processing operations in jobbing shop management. Handles retrieval and processing of special jobs for accounting periods, stock job management, and financial reconciliation. Essential for monthly accounting cycles, financial reporting, and ensuring accurate cost tracking across job lifecycles.

## Views

### MonthEndRestView

**File**: `apps/job/views/month_end_rest_view.py`
**Type**: Class-based view (APIView)
**URL**: `/rest/month-end/`

#### What it does

- Provides REST API endpoints for month-end processing operations
- Retrieves special jobs data for accounting period reconciliation
- Handles bulk job processing for month-end closure
- Manages stock job data for inventory and material cost tracking
- Supports financial reporting and accounting period management

#### Integration

- MonthEndService for business logic delegation
- CSRF exemption for API compatibility
- JSON payload processing for bulk operations
- Error handling and validation for processing operations

### get (Retrieve Month-End Data)

**File**: `apps/job/views/month_end_rest_view.py`
**Type**: Method within MonthEndRestView

#### What it does

- Retrieves special jobs and stock data for month-end processing
- Formats job history with time and cost information
- Provides stock job data with material tracking
- Enables financial review and reconciliation workflows
- Supports accounting period analysis and reporting

#### Parameters

- No parameters required

#### Returns

- **200 OK**: Month-end data with jobs and stock information
  - `jobs`: Array of special jobs with detailed history
    - `job_id`: Job UUID identifier
    - `job_number`: Job number for reference
    - `job_name`: Job name and description
    - `client_name`: Associated client name
    - `history`: Array of historical data with dates, hours, and costs
    - `total_hours`: Aggregate hours for the job
    - `total_dollars`: Aggregate cost for the job
  - `stock_job`: Stock job data with material information
    - `job_id`: Stock job UUID identifier
    - `job_number`: Stock job number
    - `job_name`: Stock job name
    - `history`: Array of material history with dates, line counts, and costs

#### Integration

- MonthEndService.get_special_jobs_data for job data retrieval
- MonthEndService.get_stock_job_data for stock information
- Job and client model data for comprehensive information
- Financial calculation and aggregation for reporting

### post (Process Month-End Jobs)

**File**: `apps/job/views/month_end_rest_view.py`
**Type**: Method within MonthEndRestView

#### What it does

- Processes selected jobs for month-end closure
- Handles bulk job processing operations
- Manages financial reconciliation and status updates
- Provides processing results with success and error reporting
- Enables controlled month-end workflow execution

#### Parameters

- JSON body with processing data:
  - `job_ids`: Array of job UUIDs to process (required)

#### Returns

- **200 OK**: Processing results with success and error information
  - `processed`: Array of successfully processed job UUIDs
  - `errors`: Array of error messages for failed processing
- **400 Bad Request**: Invalid JSON payload or malformed job_ids

#### Integration

- MonthEndService.process_jobs for business logic execution
- JSON payload validation and parsing
- Error aggregation and reporting for failed operations
- Bulk processing with individual result tracking

## Error Handling

- **400 Bad Request**: Invalid JSON payload, malformed job_ids array, or validation errors
- **500 Internal Server Error**: System failures during data retrieval or processing
- JSON parsing validation with clear error messages
- Service layer error propagation with detailed reporting
- Graceful handling of partial processing failures

## Business Rules

- Special jobs require month-end processing for accounting closure
- Stock jobs track material consumption and inventory costs
- Processing operations are bulk-enabled for efficiency
- Historical data maintains chronological ordering for analysis
- Financial calculations aggregate hours and costs accurately
- Error reporting enables troubleshooting of processing failures

## Integration Points

- **MonthEndService**: Business logic for all month-end operations
- **Job Model**: Job data retrieval and status management
- **Client Model**: Customer information for reporting
- **Time Tracking**: Historical hours and cost aggregation
- **Stock Management**: Material consumption and cost tracking

## Performance Considerations

- Efficient bulk processing for multiple jobs
- Optimized data serialization for large datasets
- Service layer optimization for complex financial calculations
- Error handling without blocking successful operations
- Historical data aggregation with database optimization

## Security Considerations

- CSRF exemption with careful API design
- Input validation for job ID arrays
- Error message sanitization to prevent information leakage
- Processing authorization and access control
- Audit logging for month-end operations

## Financial Reporting Features

- **Historical Tracking**: Complete job history with dates and costs
- **Aggregation**: Total hours and dollars for comprehensive reporting
- **Stock Integration**: Material costs and inventory tracking
- **Client Attribution**: Customer association for billing and analysis
- **Error Reporting**: Processing failures with detailed diagnostics

## Accounting Integration

- **Period Management**: Month-end closure and reconciliation
- **Cost Tracking**: Accurate labor and material cost allocation
- **Audit Trail**: Processing history and error logging
- **Bulk Operations**: Efficient processing of multiple jobs
- **Reconciliation**: Special job handling for accounting accuracy

## Related Views

- Job management views for individual job operations
- Month-end template views for web interface
- Accounting views for financial reporting
- Stock views for inventory management
- Timesheet views for labor cost tracking
