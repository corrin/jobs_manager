# REST API Reference

## Overview

This document describes the actual API endpoints implemented in the Morris Sheetmetal Works job management system. The API supports both legacy Django template functionality and the modern Vue.js frontend.

## Authentication

### JWT Authentication
The primary authentication method for modern clients:

```http
POST /accounts/api/token/
Content-Type: application/json

{
  "username": "staff_username",
  "password": "staff_password"
}
```

Response:
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### Other Authentication Endpoints
- `POST /accounts/api/token/refresh/` - Refresh JWT token
- `POST /accounts/api/token/verify/` - Verify JWT token
- `GET /accounts/me/` - Get current user profile
- `POST /accounts/logout/` - Logout user

### Using JWT Tokens
Include in Authorization header:
```http
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

## Core System APIs

### Company Defaults
- `GET /api/company-defaults/` - Get company default settings

### Enums
- `GET /api/enums/<str:enum_name>/` - Get enum choices for dropdowns

## Job Management APIs

### Legacy Job APIs (`/job/api/`)
- `POST /job/api/create-job/` - Create new job
- `POST /job/api/autosave-job/` - Auto-save job data
- `GET /job/api/fetch_job_pricing/` - Get job pricing data
- `GET /job/api/fetch_status_values/` - Get available job statuses
- `DELETE /job/api/job/<uuid:job_id>/delete/` - Delete job
- `POST /job/api/job/toggle-complex-job/` - Toggle complex job mode
- `POST /job/api/job-event/<uuid:job_id>/add-event/` - Add job event
- `GET /job/api/company_defaults/` - Get company defaults

### Modern Job REST APIs (`/job/rest/`)
- `POST /job/rest/jobs/` - Create job
- `GET /job/rest/jobs/<uuid:job_id>/` - Get job details
- `PUT /job/rest/jobs/<uuid:job_id>/` - Update job (autosave)
- `DELETE /job/rest/jobs/<uuid:job_id>/` - Delete job
- `POST /job/rest/jobs/toggle-complex/` - Toggle complex mode
- `POST /job/rest/jobs/<uuid:job_id>/events/` - Add job events

### Job Costing APIs
- `GET /job/rest/jobs/<uuid:pk>/cost_sets/<str:kind>/` - Get cost sets (kind: estimate|actual)
- `POST /job/rest/jobs/<uuid:job_id>/cost_sets/actual/cost_lines/` - Create cost line
- `PUT /job/rest/cost_lines/<int:cost_line_id>/` - Update cost line
- `DELETE /job/rest/cost_lines/<int:cost_line_id>/delete/` - Delete cost line

### Job Entry APIs
- `POST /job/rest/jobs/<uuid:job_id>/time-entries/` - Add time entry to job
- `POST /job/rest/jobs/<uuid:job_id>/material-entries/` - Add material entry to job
- `POST /job/rest/jobs/<uuid:job_id>/adjustment-entries/` - Add adjustment entry to job

### Kanban Board APIs
- `GET /job/api/jobs/fetch-all/` - Get all jobs for kanban board
- `PUT /job/api/jobs/<str:job_id>/update-status/` - Update job status
- `PUT /job/api/jobs/<uuid:job_id>/reorder/` - Reorder jobs in kanban
- `GET /job/api/jobs/fetch/<str:status>/` - Get jobs by status
- `GET /job/api/jobs/fetch-by-column/<str:column_id>/` - Get jobs by column
- `GET /job/api/jobs/status-values/` - Get available status values
- `POST /job/api/jobs/advanced-search/` - Advanced job search

### Job Files APIs
- `POST /job/api/job-files/` - Upload job file
- `GET /job/api/job-files/<int:job_number>/` - Check if job file exists
- `GET /job/api/job-files/<path:file_path>/` - Download job file
- `DELETE /job/api/job-files/<int:file_path>/` - Delete job file

### Job Archive APIs
- `GET /job/api/job/completed/` - Get completed jobs
- `POST /job/api/job/completed/archive/` - Archive completed jobs

### Quote Integration APIs
- `POST /job/rest/jobs/<uuid:pk>/quote/link/` - Link Google Sheets quote to job
- `GET /job/rest/jobs/<uuid:pk>/quote/preview/` - Preview quote data
- `POST /job/rest/jobs/<uuid:pk>/quote/apply/` - Apply quote data to job
- `GET /job/rest/jobs/<uuid:job_id>/quote/status/` - Get quote import status

### Workshop APIs
- `GET /job/rest/jobs/<uuid:job_id>/workshop-pdf/` - Generate workshop PDF

## Timesheet APIs

### Modern Timesheet APIs (`/timesheets/api/`)
- `GET /timesheets/api/staff/` - Get staff list for timesheets
- `GET /timesheets/api/jobs/` - Get jobs available for time entry
- `GET /timesheets/api/entries/` - Get time entries (supports filtering)
- `POST /timesheets/api/entries/` - Create new time entry
- `PUT /timesheets/api/entries/<uuid:entry_id>/` - Update time entry
- `DELETE /timesheets/api/entries/<uuid:entry_id>/` - Delete time entry
- `POST /timesheets/api/autosave/` - Auto-save timesheet data

### Daily Timesheet APIs
- `GET /timesheets/api/daily/` - Get daily timesheet summary
- `GET /timesheets/api/daily/<str:target_date>/` - Get daily summary for specific date
- `GET /timesheets/api/staff/<str:staff_id>/daily/` - Get staff daily timesheet detail
- `GET /timesheets/api/staff/<str:staff_id>/daily/<str:target_date>/` - Get staff daily for specific date

### Weekly Timesheet APIs
- `GET /timesheets/api/weekly/` - Get weekly timesheet overview
- `POST /timesheets/api/weekly/` - Submit paid absence request

### Alternative Timesheet APIs (`/job/rest/timesheet/`)
- `GET /job/rest/timesheet/entries/` - Get timesheet entries
- `POST /job/rest/timesheet/entries/` - Create timesheet entry
- `GET /job/rest/timesheet/staff/<uuid:staff_id>/date/<str:entry_date>/` - Get daily timesheet for staff
- `GET /job/rest/timesheet/jobs/<uuid:job_id>/` - Get timesheet data for specific job

### IMS Export
- `POST /timesheets/api/ims-export/` - Export timesheet data to IMS format

## Staff Management APIs

### Staff APIs (`/accounts/api/staff/`)
- `GET /accounts/api/staff/all/` - Get all staff members (legacy)
- `GET /accounts/api/staff/rates/<uuid:staff_id>/` - Get staff wage/charge rates
- `GET /accounts/api/staff/` - List staff members
- `POST /accounts/api/staff/` - Create new staff member
- `GET /accounts/api/staff/<uuid:pk>/` - Get staff member details
- `PUT /accounts/api/staff/<uuid:pk>/` - Update staff member
- `DELETE /accounts/api/staff/<uuid:pk>/` - Delete staff member

## Client Management APIs

### Legacy Client APIs (`/clients/api/`)
- `GET /clients/api/client/<uuid:client_id>/contacts/` - Get client contacts
- `POST /clients/api/client/contact/` - Create client contact
- `GET /clients/api/client/contact/<uuid:contact_id>/` - Get contact details

### Modern Client REST APIs (`/clients/rest/`)
- `GET /clients/rest/all/` - Get all clients
- `POST /clients/rest/create/` - Create new client
- `GET /clients/rest/search/` - Search clients (supports query parameter)
- `GET /clients/rest/<uuid:client_id>/contacts/` - Get contacts for specific client
- `POST /clients/rest/contacts/` - Create new client contact

## Purchasing APIs

### Purchase Order APIs (`/purchasing/api/`)
- `POST /purchasing/api/purchase-orders/autosave/` - Auto-save purchase order
- `GET /purchasing/api/purchase-orders/<uuid:purchase_order_id>/pdf/` - Generate PO PDF
- `POST /purchasing/api/purchase-orders/<uuid:purchase_order_id>/email/` - Email purchase order
- `POST /purchasing/api/supplier-quotes/extract/` - Extract supplier quote data

### Stock Management APIs
- `POST /purchasing/api/stock/create/` - Create new stock item
- `POST /purchasing/api/stock/consume/` - Consume stock for job
- `DELETE /purchasing/api/stock/<uuid:stock_id>/deactivate/` - Deactivate stock item
- `GET /purchasing/api/stock/search/` - Search available stock

### Delivery Receipt APIs
- `POST /purchasing/api/delivery-receipts/process/` - Process delivery receipt

### Modern Purchasing REST APIs (`/purchasing/rest/`)
- `GET /purchasing/rest/xero-items/` - Get Xero inventory items
- `GET /purchasing/rest/purchase-orders/` - List purchase orders
- `POST /purchasing/rest/purchase-orders/` - Create purchase order
- `GET /purchasing/rest/purchase-orders/<uuid:pk>/` - Get purchase order details
- `GET /purchasing/rest/delivery-receipts/` - List delivery receipts
- `POST /purchasing/rest/delivery-receipts/` - Create delivery receipt
- `GET /purchasing/rest/stock/` - List stock items
- `POST /purchasing/rest/stock/<uuid:stock_id>/consume/` - Consume stock item
- `PUT /purchasing/rest/stock/<uuid:stock_id>/` - Update stock item

## Xero Integration APIs

### Authentication & Connection
- `GET /api/xero/authenticate/` - Start Xero OAuth flow
- `GET /api/xero/oauth/callback/` - Xero OAuth callback handler
- `POST /api/xero/disconnect/` - Disconnect Xero integration
- `GET /api/xero/ping/` - Test Xero API connection

### Synchronization
- `GET /api/xero/sync-stream/` - Stream Xero sync progress (Server-Sent Events)
- `POST /api/xero/sync/` - Start Xero synchronization
- `GET /api/xero/sync-info/` - Get current sync status information

### Document Management
- `POST /api/xero/create_invoice/<uuid:job_id>/` - Create Xero invoice for job
- `DELETE /api/xero/delete_invoice/<uuid:job_id>/` - Delete Xero invoice
- `POST /api/xero/create_quote/<uuid:job_id>/` - Create Xero quote for job
- `DELETE /api/xero/delete_quote/<uuid:job_id>/` - Delete Xero quote
- `POST /api/xero/create_purchase_order/<uuid:purchase_order_id>/` - Create Xero purchase order
- `DELETE /api/xero/delete_purchase_order/<uuid:purchase_order_id>/` - Delete Xero purchase order

## Quoting APIs

### Price List Management (`/quoting/api/`)
- `POST /quoting/api/extract-supplier-price-list/` - Extract pricing from supplier documents

### Background Jobs (Django-RQ)
- `GET /quoting/api/django-jobs/` - List background jobs
- `POST /quoting/api/django-jobs/` - Create background job
- `GET /quoting/api/django-jobs/<int:id>/` - Get job details
- `GET /quoting/api/django-job-executions/` - List job executions

### MCP (Model Context Protocol) APIs
- `GET /quoting/api/mcp/search_stock/` - Search stock via MCP
- `GET /quoting/api/mcp/search_supplier_prices/` - Search supplier prices via MCP
- `GET /quoting/api/mcp/job_context/<uuid:job_id>/` - Get job context for MCP

## Accounting APIs

### Quote Management (`/accounting/api/`)
- `GET /accounting/api/quote/<uuid:job_id>/pdf-preview/` - Generate quote PDF preview
- `POST /accounting/api/quote/<uuid:job_id>/send-email/` - Send quote via email

### Reports
- `GET /accounting/api/reports/calendar/` - Get KPI calendar data

## Response Formats

### Success Response
```json
{
  "success": true,
  "data": { ... },
  "message": "Operation completed successfully"
}
```

### Error Response
```json
{
  "error": "Error description",
  "details": "Detailed error information"
}
```

### List Response (with pagination where applicable)
```json
{
  "results": [ ... ],
  "count": 150,
  "next": "url_to_next_page",
  "previous": null
}
```

## HTTP Status Codes

- `200 OK` - Successful GET, PUT, PATCH
- `201 Created` - Successful POST
- `204 No Content` - Successful DELETE
- `400 Bad Request` - Validation errors
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Permission denied
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

## Notes

1. **UUID Format**: All entity IDs use UUID format (e.g., `550e8400-e29b-41d4-a716-446655440000`)
2. **Date Format**: Dates use ISO 8601 format (`YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SSZ`)
3. **Authentication**: Most endpoints require authentication via JWT or session
4. **CORS**: Enabled for cross-origin requests from Vue.js frontend
5. **File Uploads**: Support multipart/form-data for file attachments
6. **Real-time**: Some endpoints support Server-Sent Events for real-time updates

This API documentation reflects the actual implementation in the Django codebase and supports both the legacy Django template frontend and the modern Vue.js frontend application.