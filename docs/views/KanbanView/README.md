# Kanban View API Documentation

## Business Purpose

Provides REST API endpoints for kanban board functionality in jobbing shop operations. Handles job visualization, status management, drag-and-drop reordering, and advanced search capabilities. Essential for visual job workflow management and real-time status tracking throughout the quote → job → invoice process.

## Views

### fetch_all_jobs

**File**: `apps/job/views/kanban_view_api.py`
**Type**: Function-based API view (GET only)
**URL**: `/job/api/kanban/jobs/all/`

#### What it does

- Retrieves all active and archived jobs for kanban board initialization
- Provides comprehensive job data for board population
- Separates active workflow jobs from archived historical records
- Optimizes data loading for kanban interface performance

#### Parameters

- No parameters required

#### Returns

- **200 OK**: JSON with active and archived job collections
  - `active_jobs`: Current workflow jobs with complete kanban data
  - `archived_jobs`: Recent archived jobs (limited to 50)
  - `total_archived`: Total count of archived jobs
- **500 Internal Server Error**: Job retrieval failures

#### Integration

- KanbanService.get_all_active_jobs() for workflow jobs
- KanbanService.get_archived_jobs() for historical data
- KanbanService.serialize_job_for_api() for consistent data format
- Authentication required for all job access

### update_job_status

**File**: `apps/job/views/kanban_view_api.py`
**Type**: Function-based API view (POST only)
**URL**: `/job/api/kanban/jobs/status/`

#### What it does

- Updates job status with kanban drag-and-drop operations
- Handles status workflow validation and transitions
- Manages job positioning within status columns
- Creates audit trail for status changes

#### Parameters

- JSON body with status update data:
  - `job_id`: UUID of job to update (required)
  - `new_status`: Target status value (required)
  - `position`: Optional position within status column

#### Returns

- **200 OK**: JSON success confirmation with updated job data
- **400 Bad Request**: Invalid status transition or validation errors
- **404 Not Found**: Job not found
- **500 Internal Server Error**: Status update failures

#### Integration

- KanbanService.update_job_status() for business logic
- Job status workflow validation
- Position management within kanban columns
- Audit trail creation for status tracking

### reorder_job

**File**: `apps/job/views/kanban_view_api.py`
**Type**: Function-based API view (POST only)
**URL**: `/job/api/kanban/jobs/reorder/`

#### What it does

- Handles job reordering within kanban columns
- Manages job priority and position adjustments
- Supports drag-and-drop interface operations
- Maintains consistent job ordering across sessions

#### Parameters

- JSON body with reordering data:
  - `job_id`: UUID of job to reorder (required)
  - `new_position`: Target position within column (required)
  - Additional ordering metadata

#### Returns

- **200 OK**: JSON success confirmation with updated ordering
- **404 Not Found**: Job not found
- **500 Internal Server Error**: Reordering failures

#### Integration

- KanbanService.reorder_job() for position management
- Job model position tracking
- Consistent ordering persistence
- Real-time UI synchronization

### fetch_jobs

**File**: `apps/job/views/kanban_view_api.py`
**Type**: Function-based API view (GET only)
**URL**: `/job/api/kanban/jobs/<str:status>/`

#### What it does

- Retrieves jobs filtered by specific status
- Supports search functionality within status groups
- Provides job counts and filtering statistics
- Optimizes loading for individual kanban columns

#### Parameters

- `status`: Job status to filter by (path parameter)
- `search`: Optional search term for job filtering (query parameter)

#### Returns

- **200 OK**: JSON with filtered job data and statistics
  - `jobs`: Filtered job collection with kanban data
  - `total`: Total jobs in status (unfiltered)
  - `filtered_count`: Count after search filtering
- **500 Internal Server Error**: Job filtering failures

#### Integration

- KanbanService.get_jobs_by_status() for status filtering
- Search term processing and job matching
- Job count statistics for UI indicators
- Pagination support for large job collections

### fetch_status_values

**File**: `apps/job/views/kanban_view_api.py`
**Type**: Function-based API view (GET only)
**URL**: `/job/api/kanban/status-values/`

#### What it does

- Returns available job status options for kanban columns
- Provides status metadata for board configuration
- Supports dynamic kanban column generation
- Enables status workflow validation

#### Parameters

- No parameters required

#### Returns

- **200 OK**: JSON with status configuration data
  - Available status choices with display names
  - Status workflow rules and transitions
  - Column configuration metadata
- **500 Internal Server Error**: Status retrieval failures

#### Integration

- KanbanService.get_status_choices() for status metadata
- Job model status configuration
- Workflow validation rules
- Dynamic UI column generation

### advanced_search

**File**: `apps/job/views/kanban_view_api.py`
**Type**: Function-based API view (GET only)
**URL**: `/job/api/kanban/search/`

#### What it does

- Performs comprehensive job search across multiple criteria
- Supports complex filtering combinations
- Enables advanced job discovery and analysis
- Provides detailed search result metadata

#### Parameters

- Multiple query parameters for search criteria:
  - `job_number`: Job number pattern matching
  - `name`: Job name search
  - `description`: Description content search
  - `client_name`: Client name filtering
  - `contact_person`: Contact person search
  - `created_by`: Creator filtering
  - `created_after`: Date range start
  - `created_before`: Date range end
  - `status`: Multiple status filtering
  - `paid`: Payment status filtering

#### Returns

- **200 OK**: JSON with comprehensive search results
  - `jobs`: Matching jobs with complete kanban data
  - `total`: Total matching job count
  - Search criteria summary
- **500 Internal Server Error**: Search processing failures

#### Integration

- KanbanService.perform_advanced_search() for complex filtering
- Multi-criteria job matching
- Date range processing and validation
- Search result optimization and ranking

### fetch_jobs_by_column

**File**: `apps/job/views/kanban_view_api.py`
**Type**: Function-based API view (GET only)
**URL**: `/job/api/kanban/columns/<str:column_id>/`

#### What it does

- Retrieves jobs for specific kanban columns using categorization system
- Supports column-based job loading and pagination
- Enables efficient kanban board rendering
- Provides column-specific job management

#### Parameters

- `column_id`: Kanban column identifier (path parameter)
- `max_jobs`: Maximum jobs to return (query parameter, default 50)
- `search`: Optional search term within column (query parameter)

#### Returns

- **200 OK**: JSON with column-specific job data
- **400 Bad Request**: Invalid column ID or parameters
- **500 Internal Server Error**: Column data retrieval failures

#### Integration

- KanbanService.get_jobs_by_kanban_column() for categorized retrieval
- Column-based job organization
- Search functionality within columns
- Pagination support for performance optimization

## Error Handling

- **400 Bad Request**: Invalid parameters, malformed data, or business rule violations
- **401 Unauthorized**: Authentication required for all kanban operations
- **404 Not Found**: Jobs or resources not found
- **500 Internal Server Error**: Service failures, database errors, or unexpected system issues
- Comprehensive logging for debugging and monitoring
- Graceful error responses for frontend handling

## Data Serialization

- KanbanService.serialize_job_for_api() provides consistent job data format
- Complete job information including client, status, pricing, and metadata
- Optimized data structure for kanban interface requirements
- Request context integration for user-specific data

## Integration Points

- KanbanService for all business logic delegation
- Job model for data persistence and retrieval
- Authentication system for access control
- Frontend kanban interface for real-time updates
- Audit system for change tracking

## Performance Considerations

- Job data pagination for large datasets
- Efficient database queries with proper indexing
- Cached status configurations for quick access
- Optimized serialization for minimal data transfer
- Search query optimization for fast results

## Related Views

- Job management views for detailed job operations
- Job editing views for job modification
- Authentication views for access control
- Audit views for change tracking and history
