# Job Sheet Additional Fields Implementation Plan

## Overview

Add four new fields to the printed job sheet (workshop PDF):
1. Contact phone number
2. Due date (delivery_date)
3. Workshop time allocated
4. Pricing methodology (Quoted vs T&M)

## Current Implementation

The job sheet is generated in `apps/job/services/workshop_pdf_service.py` using ReportLab.

**Key functions:**
- `create_workshop_pdf(job)` - Entry point
- `add_job_details_table(pdf, y_position, job)` - Renders job details table at lines 259-311

**Current fields in job details table:**
- Client name (header row)
- Contact name (header row)
- Description
- Notes (HTML formatted)
- Entry date (created_at)
- Order number

## Data Sources

### Available on Job Model

Located in `apps/job/models/job.py`:

1. **Contact phone** - `job.contact.phone`
   - Via ForeignKey to ClientContact (line 62-69)
   - Field: `contact.phone` (need to verify ClientContact model has phone field)

2. **Due date** - `job.delivery_date`
   - Field: `delivery_date` (line 81)
   - Type: DateField, nullable

3. **Pricing methodology** - `job.pricing_methodology`
   - Field: `pricing_methodology` (line 97-104)
   - Choices: `time_materials` or `fixed_price`
   - Display values: "Time & Materials" or "Fixed Price"

4. **Workshop time allocated** - **NOT CURRENTLY STORED**
   - Need to determine data source:
     - Option A: Sum of time entries for this job?
     - Option B: Estimated hours from quote/cost set?
     - Option C: New field on Job model?
   - **ACTION REQUIRED**: Clarify with user what "workshop time allocated" means

## Implementation Steps

### 1. Verify ClientContact phone field
- Check `apps/client/models.py` for ClientContact model
- Confirm phone field exists
- If not, determine alternative (client.phone?)

### 2. Determine workshop time allocated source
- **BLOCKED**: Need clarification from user
- Possible sources:
  - `CostSet` → `CostLine` entries with type="labour"
  - Aggregated time entries from staff
  - New field to be added
- ANSWER: You're reaading from the estimate time entries, and you skip the "Estimated Office Time" entry.

### 3. Update job details table in PDF service

Modify `add_job_details_table()` in `apps/job/services/workshop_pdf_service.py`:

**Add new rows to `job_details` list (after line 284):**

```python
[
    Paragraph("CONTACT PHONE", label_style),
    Paragraph(job.contact.phone if job.contact and job.contact.phone else "N/A", body_style),
],
[
    Paragraph("DUE DATE", label_style),
    job.delivery_date.strftime("%d %b %Y") if job.delivery_date else "N/A",
],
[
    Paragraph("PRICING TYPE", label_style),
    Paragraph(dict(Job.PRICING_METHODOLOGY_CHOICES).get(job.pricing_methodology, "N/A"), body_style),
],
[
    Paragraph("WORKSHOP TIME ALLOCATED", label_style),
    Paragraph(f"{workshop_hours:.1f} hours" if workshop_hours else "N/A", body_style),
],
```

**Notes:**
- Use same formatting pattern as existing fields
- Handle None values gracefully with "N/A"
- Format dates consistently with entry date format
- Display human-readable pricing methodology

### 4. Testing Considerations

**Test cases:**
- Job with all fields populated
- Job with missing contact
- Job with missing due date
- Job with each pricing methodology
- Job with no workshop time allocated
- Verify PDF layout doesn't break with additional rows
- Check page breaks if table gets too long

### 5. Files to Modify

**Primary:**
- `apps/job/services/workshop_pdf_service.py` - Add fields to table

**Investigation needed:**
- `apps/client/models.py` - Verify ClientContact.phone exists
- `apps/job/models/costing.py` - If workshop time comes from CostSet
- `apps/job/models/job.py` - May need to add workshop_hours field

## Open Questions

1. **Workshop time allocated** - What is the data source?
   - Estimated hours from quote?
   - Sum of actual time entries?
   - Budgeted/allocated hours (new field)?

2. **Contact phone** - If ClientContact doesn't have phone, should we:
   - Use Client.phone instead?
   - Add phone field to ClientContact?
   - Show "N/A"?

3. **Field ordering** - Where should these fields appear in the table?
   - After existing fields?
   - Specific order preference?

## Risk Assessment

**Low risk:**
- Due date, pricing methodology - straightforward fields
- PDF formatting - using existing patterns

**Medium risk:**
- Contact phone - depends on data model structure
- Workshop time allocated - data source unclear

**Mitigation:**
- STRICTLY AVOID Defensive coding with None checks
- INSTEAD EXPLICITLY CHECK FOR INVALID AND LOG/HANDLE ERRORS, or return failure.
- OBVIOUSLY, this doesn't apply for fields that are nullable
- Default to "N/A" for missing data, and log to persist_app_error.
- Test with various job states
