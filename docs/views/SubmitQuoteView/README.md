# Submit Quote View Documentation

## Business Purpose
Handles customer-facing quote presentation workflow for jobbing shop operations. Generates professional PDF quote summaries and facilitates email communication with clients. **Note**: This is separate from Xero accounting quote creation - these views create presentation documents for customers, while Xero quotes are handled by `XeroQuoteManager` in the workflow app for accounting system integration.

## Views

### generate_quote_pdf
**File**: `apps/accounting/views/submit_quote_view.py`
**Type**: Function-based view
**URL**: `/accounting/api/quote/<uuid:job_id>/pdf-preview/`

#### What it does
- Generates professional PDF quote summary for customer presentation
- Includes job details, pricing breakdown, and company branding
- Exports time entries, material entries, and adjustment entries in tabular format
- Creates downloadable PDF file for quote submission

#### Parameters
- `job_id`: UUID of the job to generate quote PDF for

#### Returns
- FileResponse containing PDF document
- Content-Type: `application/pdf`
- Filename: `quote_summary_{job.name}.pdf`

#### Integration
- Uses Job model and latest_quote_pricing relationship
- Accesses JobPricing time_entries, material_entries, adjustment_entries
- Includes company logo from static files
- No direct Xero integration (uses internal pricing data)

### send_quote_email
**File**: `apps/accounting/views/submit_quote_view.py`
**Type**: Function-based view (CSRF exempt)
**URL**: `/accounting/api/quote/<uuid:job_id>/send-email/`

#### What it does
- Prepares quote email for client communication
- Generates PDF attachment and mailto URL
- Supports both quote submission and follow-up email types
- Extracts client email from job relationship

#### Parameters
- `job_id`: UUID of the job to send quote for
- `contact_only`: Query parameter (optional) - when "true", sends follow-up email instead of quote

#### Returns
- JSON response containing:
  - `success`: Boolean status
  - `mailto_url`: Pre-formatted mailto link with subject/body
  - `pdf_content`: Base64-encoded PDF for download
  - `pdf_name`: Suggested filename for PDF attachment

#### Integration
- Uses Job → Client → email relationship for recipient
- Generates PDF using same logic as generate_quote_pdf
- Uses workflow.utils.extract_messages for error handling
- No email server integration (creates mailto links for client email software)

## Error Handling
- **400 Bad Request**: Client email not found for job
- **404 Not Found**: Job with specified ID does not exist
- **500 Internal Server Error**: PDF generation failures or unexpected errors
- Comprehensive logging for troubleshooting email and PDF generation issues

## Related Views
- Job management views for job data source
- Client views for email address management
- JobPricing views for quote data structure
- KPI views for business analytics on quote success rates
