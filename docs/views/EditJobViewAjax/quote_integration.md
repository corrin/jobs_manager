# Quote Integration Views

## Business Purpose

Handles integration between job management and external quote systems, particularly Google Sheets quote synchronization. Enables seamless quote import and linking for accurate job pricing and estimation workflows in jobbing shop operations.

## Views

### create_linked_quote_api

**File**: `apps/job/views/edit_job_view_ajax.py`
**Type**: Function-based API view (POST only)
**URL**: `/job/api/create-linked-quote/`

#### What it does

- Creates linked quotes from external quote systems (Google Sheets)
- Integrates job pricing with external quote data
- Handles quote validation and data transformation
- Manages quote-to-job pricing synchronization

#### Parameters

- JSON body with quote linking data:
  - `job_id`: Job UUID to link quote to (required)
  - `quote_sheet_url`: Google Sheets URL for quote data (required)
  - `quote_data`: Quote structure and pricing information
  - Additional quote metadata and configuration

#### Returns

- **201 Created**: JSON with created quote link and pricing data
- **400 Bad Request**: Invalid quote data, URL validation errors, or job state issues
- **404 Not Found**: Job not found
- **409 Conflict**: Quote already linked or pricing conflicts
- **500 Internal Server Error**: Quote processing failures or external system errors

#### Integration

- link_quote_sheet() service for Google Sheets integration
- Quote validation and data transformation
- Job pricing synchronization and update
- External system authentication and access management
- Quote revision tracking and version control

## Quote Data Processing

### Google Sheets Integration

- Authentication with Google Sheets API
- Quote data extraction and validation
- Pricing structure transformation
- Material and labor cost breakdown
- Quote revision and update tracking

### Data Validation

- Quote structure verification
- Pricing calculation validation
- Material quantity and cost checks
- Labor hour and rate validation
- Total cost and revenue reconciliation

### Job Pricing Synchronization

- Quote data transformation to job pricing format
- Cost breakdown mapping (materials, labor, adjustments)
- Pricing stage management (estimate → quote → actual)
- Historical pricing preservation
- Revision tracking and audit trails

## Business Rules

### Quote Linking Constraints

- Jobs must be in appropriate status for quote linking
- Quote data must pass validation checks
- Pricing totals must reconcile with job requirements
- External quote accessibility verification
- User permissions for quote operations

### Data Integrity Requirements

- Quote data consistency across systems
- Pricing calculation accuracy
- Material and labor cost validation
- Revenue projection accuracy
- Historical data preservation

### Synchronization Rules

- Quote updates trigger job pricing updates
- Version control for quote revisions
- Conflict resolution for concurrent updates
- Backup and recovery for external data loss
- Audit trail maintenance for all changes

## Error Handling

- **400 Bad Request**: Invalid quote URLs, malformed data, or validation failures
- **401 Unauthorized**: Insufficient permissions or external system authentication failures
- **403 Forbidden**: Access denied to external quote systems
- **404 Not Found**: Job not found or external quote inaccessible
- **409 Conflict**: Quote linking conflicts or data inconsistencies
- **500 Internal Server Error**: External system failures, network issues, or processing errors

## External System Dependencies

### Google Sheets API

- Authentication and authorization management
- Rate limiting and quota management
- Error handling for API failures
- Data format standardization
- Real-time synchronization capabilities

### Quote Format Standards

- Standardized quote structure requirements
- Material and labor cost breakdown formats
- Pricing calculation methodologies
- Quote metadata and versioning
- Export and import format specifications

## Integration Points

- Job pricing system for cost synchronization
- Google Sheets API for external data access
- Authentication system for API access management
- Audit system for change tracking
- Notification system for update alerts

## Performance Considerations

- Asynchronous quote processing for large datasets
- Caching strategies for frequently accessed quotes
- Rate limiting compliance with external APIs
- Batch processing for multiple quote updates
- Error recovery and retry mechanisms

## Security Considerations

- Secure authentication with external systems
- Data encryption for sensitive pricing information
- Access control for quote operations
- Audit logging for all quote activities
- Data privacy compliance for external integrations
