# Workshop View Documentation

## Business Purpose
Provides workshop PDF generation functionality for job documentation in jobbing shop operations. Creates printable jobsheets containing job specifications, files, and instructions for workshop personnel. Essential for shop floor communication, job execution guidance, and ensuring workshop teams have complete job information during production.

## Views

### WorkshopPDFView
**File**: `apps/job/views/workshop_view.py`
**Type**: Class-based view (APIView)
**URL**: `/job/<uuid:job_id>/workshop-pdf/`

#### What it does
- Generates comprehensive workshop PDF documents for specific jobs
- Creates printable jobsheets with job specifications and instructions
- Includes job files marked for jobsheet printing
- Provides formatted documentation for workshop floor use
- Enables on-demand PDF generation for job execution

#### Parameters
- `job_id`: UUID of job to generate workshop PDF for (path parameter)

#### Returns
- **200 OK**: PDF file response for workshop jobsheet
  - Content-Type: application/pdf
  - Content-Disposition: inline for browser viewing
  - Filename: workshop_{job_number}.pdf
- **404 Not Found**: Job not found for specified ID
- **500 Internal Server Error**: PDF generation failures

#### Integration
- create_workshop_pdf service for PDF generation logic
- Job model for comprehensive job data retrieval
- JobFile integration for files marked to print on jobsheet
- FileResponse for efficient PDF delivery

### get (PDF Generation Method)
**File**: `apps/job/views/workshop_view.py`
**Type**: Method within WorkshopPDFView

#### What it does
- Handles GET requests for workshop PDF generation
- Validates job existence and retrieves job data
- Delegates PDF creation to workshop service
- Configures PDF response headers for optimal browser handling
- Provides error handling for generation failures

#### Parameters
- Same as parent WorkshopPDFView

#### Returns
- Generated PDF with proper headers for inline viewing
- Error responses for failures with detailed logging

#### Integration
- Job validation with get_object_or_404 pattern
- Workshop PDF service delegation for business logic
- FileResponse configuration for PDF delivery
- Exception handling with comprehensive logging

## PDF Content Features
- **Job Information**: Job number, name, description, and client details
- **Specifications**: Technical requirements and job specifications
- **File Attachments**: Files marked with print_on_jobsheet flag
- **Instructions**: Workshop instructions and special requirements
- **Formatting**: Professional layout optimized for workshop printing

## Error Handling
- **404 Not Found**: Job not found for specified UUID
- **500 Internal Server Error**: PDF generation failures or system errors
- Comprehensive exception logging for debugging
- User-friendly error messages for troubleshooting
- Graceful handling of service layer failures

## Business Rules
- Only existing jobs can generate workshop PDFs
- PDF content includes files marked for jobsheet printing
- Generated PDFs use job number in filename for identification
- Inline content disposition enables browser viewing
- PDF generation is on-demand for current job state

## Integration Points
- **Workshop PDF Service**: Business logic for PDF content generation
- **Job Model**: Complete job data for PDF content
- **JobFile Model**: File attachments for jobsheet inclusion
- **FileResponse**: Efficient PDF delivery to browsers
- **Logging System**: Error tracking and debugging support

## Performance Considerations
- On-demand PDF generation for current job state
- Efficient service layer delegation for PDF creation
- Optimized file response delivery
- Error handling without impacting system performance
- PDF generation with minimal database queries

## Security Considerations
- Job ID validation prevents unauthorized PDF access
- Error message sanitization to prevent information leakage
- Access control through job existence validation
- Secure PDF generation without exposing system internals
- Audit logging for PDF generation tracking

## Workshop Integration
- **Shop Floor Communication**: Clear job documentation for production
- **File Integration**: Relevant documents included in jobsheet
- **Print Optimization**: PDF formatted for workshop printing
- **Job Identification**: Clear job number and client information
- **Instruction Clarity**: Technical specifications and requirements

## File Management
- Files marked with print_on_jobsheet flag automatically included
- PDF generation respects current job file status
- Workshop-relevant documents integrated into jobsheet
- File organization optimized for production reference
- Dynamic content based on current job state

## Related Views
- Job file views for document management
- Job management views for job lifecycle
- JobFile views for file attachment workflow
- Job editing views for specification updates
- Client views for customer information integration