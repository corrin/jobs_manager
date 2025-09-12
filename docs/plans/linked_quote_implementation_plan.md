# Linked Quote Implementation Plan

## Overview

This document outlines the implementation plan for adding linked quote functionality to the jobs system. The plan breaks down the work into smaller, testable tickets to ensure stability throughout the implementation process.

## Current System Analysis

After examining the codebase, we've identified the following key components:

1. **Job Model Structure**:
   - The Job model is the central entity with fields for job details
   - Each Job has three JobPricing instances (estimate, quote, reality) that track different types of pricing
   - JobPricing contains time_entries, material_entries, and adjustment_entries
   - The Quote model is linked to a Job and contains information about the quote in Xero
   - Note that these are not stages of pricing.  An estimate can be edited after a quote is sent, or even part way through a job.

2. **UI Components**:
   - The job edit page has sections for Estimate, Quote, and Reality
   - Each section has tables for time, materials, and adjustments
   - The UI supports both simple and complex (itemized) pricing views

## Proposed Changes

1. **Parts Concept**: Restructure job pricing to use parts, where each part contains time entries, material entries, and adjustments (MAJOR CHANGE)
2. **Add Linked Quote Field**: Jobs will have an optional link to a Google Sheets spreadsheet
3. **Google Sheets Integration**: Implement API integration to read/write from Google Sheets
4. **Master Template**: Add a template URL to CompanyDefaults and functionality to duplicate it
5. **UI Updates**: Make tables readonly when a job has a linked quote and add UI for managing parts

## Implementation Tickets

### Ticket 0: Data model fixes

Add parts to job pricing, and remove the time/material/adjustment entries
Ensure job pricing has a default part
Move all existing data to that default part
TEST EVERYTHING

After this change, everything MUST go through the parts.  I.e. you cannot get the time entries for a job pricing.
This requires fixing the APIs, the serialisers, the JS, etc.

No UI changes.

### Ticket 1: Add Linked Quote Field and Master Template to Company Defaults
**Goal**: Add the basic fields needed for linked quotes without changing functionality.

1. Add `linked_quote` URL field to the Job model
2. Add `master_quote_template_url` field to CompanyDefaults model
3. Create migration for these changes
4. Update the job edit form to display the linked quote field (read-only for now)

**Technical Details**:
- The `linked_quote` field should be a URLField with null=True, blank=True
- The `master_quote_template_url` field should be a URLField with null=True, blank=True
- The migration should be non-destructive and backward compatible

**Now Test**: Verify the application runs normally and the new fields appear in the admin interface but don't affect existing functionality.

### Ticket 2: Google Sheets API Integration Setup
**Goal**: Set up the foundation for Google Sheets integration.

1. Add Google Sheets API client library to the project
2. Create a service for Google Sheets authentication and basic operations
3. Add configuration for Google API credentials
4. Create simple test functions to verify API connectivity

**Technical Details**:
- Use the official Google API Python client library
- Create a new service module in workflow/services/google_sheets_service.py
- Store credentials securely, possibly using environment variables
- Implement basic operations: read spreadsheet, write to spreadsheet, duplicate spreadsheet

**Now Test**: Verify the application can connect to Google Sheets API and perform basic operations like reading a spreadsheet.

### Ticket 3: Master Template Duplication Functionality
**Goal**: Implement the ability to duplicate the master quote template.

1. Add functionality to duplicate the master template spreadsheet
2. Create a service method to generate a new spreadsheet from the template
3. Add a UI button to create a new linked quote from the template
4. Update the job edit form to display the linked quote URL as a clickable link

**Technical Details**:
- Extend the Google Sheets service to support template duplication
- Add a new button to the job edit page near the job details section
- Implement a new API endpoint for creating a linked quote
- Update the job serializer to include the linked_quote field

**Now Test**: Create a new job, click the "Create Linked Quote" button, and verify a new spreadsheet is created and linked to the job.

Ticket 4a: Create Part Model and Schema
Goal:
Add a Part model, preparing for parts-based job pricing.

Tasks:

Create new Part model with the following fields:

id (UUID, primary key)

job_pricing (ForeignKey to JobPricing, required)

name (CharField, required)

description (TextField, optional)

created_at, updated_at (DateTimeField, auto-managed)

Add a nullable part ForeignKey to all entry models (TimeEntry, MaterialEntry, AdjustmentEntry), to enable migration.

Ticket 4b: Data Migration — Assign Entries to Main Work
Goal:
Ensure every existing and future entry is associated with a Part.

Tasks:

For every existing JobPricing, create a single Part named “Main Work”.

For every entry (time, material, adjustment) under that JobPricing that doesn’t have a Part, assign it to the new “Main Work” part.

Ensure new entries always require a Part going forward.

Ticket 4c: Update Serializers and Models
Goal:
Reflect the new parts-based structure in all relevant serializers and model validation.

Tasks:

Update entry model fields so part is required (null=False, blank=False) after migration.

Update all serializers (JobPricingSerializer, TimeEntrySerializer, etc.) to nest/reflect the new Parts structure (i.e., JobPricing serializes its parts, and each part serializes its own entries).

Update or add model constraints so every entry must be attached to a Part.

Ticket 4d: Minimal UI/Admin Adjustment
Goal:
Allow basic management of parts in admin, without changing the main user UI yet.

Tasks:

Register Part with Django admin.

(Optional) Make sure admin/console users can see and manage entries by Part, for QA and data integrity.

Ticket 4e: Clean Up and Finalize Schema
Goal:
Remove legacy/flat entry relationships and enforce the new structure.

Tasks:

Remove any now-obsolete direct entry relationships on JobPricing (if any).

Update business logic and documentation to clarify:

All entries must belong to a Part.

All JobPricing records will always have at least one Part (“Main Work” if not split).
**Now Test**: Verify existing jobs still display correctly and all functionality works as before.

### Ticket 5: Update UI for Parts in Job Edit Page
**Goal**: Modify the UI to display and manage parts.

1. Update the job edit page to show parts as rows in a single table
2. Add UI controls to add/edit/delete parts
3. Ensure the default "Other Work" part is always present
4. Update the grid logic to handle the parts structure

**Major UI Shift**: Rather than having a single table for time, materials, and adjustments, we will have a single table for parts. This table will have a column for the Part Name, Time (hours), Time Cost, Time Retail, Material Cost, Material Retail, Adjustment Cost, Adjustment Retail. The itemized pricing toggle changes visibility: false shows total across all parts, true shows one row per part.

#### **Ticket 5.1: Core UI Table Structure & Default Part Display**

*   **Goal**: Establish the foundational HTML structure in `edit_job_ajax.html` for a single parts entry table, and ensure the default "Other Work" part is always present as a row.
*   **Tasks**:
    1.  Modify `edit_job_ajax.html` to remove the existing time, material, and adjustment tables.
    2.  Introduce a new single table structure (e.g., a `div` for the grid) that will house the parts data.
    3.  Ensure that if no parts are explicitly defined for a job, a default "Other Work" part is represented as a row in this new table.
    4.  Define the initial table headers for the new structure: "Part Name, Time (hours), Time Cost, Time Retail, Material Cost, Material Retail, Adjustment Cost, Adjustment Retail".
*   **Technical Details**:
    *   Focus on `job/templates/jobs/edit_job_ajax.html`.
    *   This ticket focuses on the HTML scaffolding, not the dynamic grid population yet.
*   **Now Test**: Verify that the job edit page loads, the old tables are gone, and a new table structure is present with the correct headers. Confirm that a row representing "Other Work" is visible by default if no other parts exist.

#### **Ticket 5.2: Part Management UI Controls (Add/Edit/Delete)**

*   **Goal**: Implement the client-side UI controls and associated JavaScript functions for adding, editing, and deleting parts, integrated directly into the single parts table's row operations.
*   **Tasks**:
    1.  Implement functionality to add new part rows (e.g., by pressing Enter on the last row, or a similar grid-native mechanism).
    2.  Implement functionality to delete part rows (e.g., via a trash can icon within the row, or a similar grid-native mechanism).
    3.  Ensure that editing part details (e.g., Part Name) is handled directly within the grid cells.
    4.  Implement JavaScript functions to handle these row-based actions, including dynamically updating the single parts table.
    5.  Integrate with the backend API endpoints for creating, updating, and deleting `Part` objects (assuming these API endpoints are already available from Ticket 4).
*   **Technical Details**:
    *   Focus on `job/static/job/js/edit_job_grid_logic.js` and potentially `job/static/job/js/grid/grid_options.js` to configure grid behavior for row addition/deletion.
    *   Utilize existing AJAX patterns for communication with the Django backend.
*   **Now Test**: Verify that new part rows can be added (e.g., by pressing Enter), existing part rows can be deleted (e.g., via a trash can icon), and part details can be edited directly in the grid. Confirm these changes persist after page refresh.

#### **Ticket 5.3: Grid Logic, Itemized Pricing Toggle, & Editability**

*   **Goal**: Adapt the existing grid logic in `edit_job_grid_logic.js` to populate the single parts table with data, correctly implement the itemized pricing toggle, and manage grid editability based on the number of parts.
*   **Tasks**:
    1.  Refactor `edit_job_grid_logic.js` to initialize and manage the *single* parts grid.
    2.  Update grid data sources to fetch all parts and their associated time, material, and adjustment entry data.
    3.  Configure grid column definitions to match the new structure: "Part Name, Time (hours), Time Cost, Time Retail, Material Cost, Material Retail, Adjustment Cost, Adjustment Retail".
    4.  Implement the logic for the "itemized pricing toggle":
        *   If `false`, the grid should display a single summary row aggregating all costs across all parts.
        *   If `true`, the grid should display one row for each part.
    5.  **Crucially, implement editability logic**:
        *   If the job has **multiple parts** AND the "itemized pricing toggle" is `false` (summary view), the grid must be marked **non-editable**.
        *   Display a message to the user, e.g., "Pricing of multiple parts requires itemized pricing."
        *   Otherwise (single part, or multiple parts with itemized pricing true), the grid should be editable.
    6.  Ensure existing grid functionalities (e.g., editing cells, calculations) work correctly within this new single-table, parts-based structure when editable.
*   **Technical Details**:
    *   Heavy modifications to `job/static/job/js/edit_job_grid_logic.js`.
    *   Potential changes to `job/static/job/js/grid/grid_options.js` for new column definitions, data aggregation, and editability settings.
    *   Requires understanding how the backend now provides data (nested parts with entries).
*   **Now Test**: Verify that the single grid correctly displays data grouped by parts (when itemized), and that the itemized pricing toggle switches between the summary view and the per-part view as expected. Test editing values within the grid and ensure they update correctly when editable. Crucially, test a job with multiple parts where itemized pricing is off, and confirm the grid is non-editable with the correct message.

#### **Ticket 5.4: UI Graceful Handling & Data Consistency**

*   **Goal**: Ensure the UI gracefully handles jobs with and without parts, and that data consistency is maintained during UI interactions and saves.
*   **Tasks**:
    1.  Review all UI components and JavaScript logic to ensure they function correctly for jobs created *before* the parts migration (which would have a single "Main Work" part) and new jobs.
    2.  Implement client-side validation for part names and other fields within the grid.
    3.  Ensure that when entries (time, material, adjustment) are added or edited via the grid, they are correctly associated with the respective part row.
    4.  Verify that the autosave functionality (`edit_job_form_autosave.js`) correctly handles the new parts table structure when saving job data.
    5.  Perform comprehensive end-to-end testing of the entire job edit page with the new parts UI.
*   **Technical Details**:
    *   Cross-cutting concerns affecting `edit_job_ajax.html`, `edit_job_grid_logic.js`, `edit_job_form_autosave.js`, and any new part-related JavaScript files.
    *   Focus on robust error handling and user feedback.
*   **Now Test**: Create new jobs, add multiple parts, add entries to different parts, and verify all data is saved and displayed correctly. Test existing jobs to ensure they still function as expected with the "Other Work" part.

### Visualizing the UI Shift (Corrected High-Level)

```mermaid
graph TD
    A[Job Edit Page] --> B{Itemized Pricing Toggle}
    B -- False --> C[Single Parts Table (Summary View)]
    C -- Columns --> C1(Total Time Hours)
    C -- Columns --> C2(Total Time Cost)
    C -- Columns --> C3(Total Material Cost)
    C -- Columns --> C4(Total Adjustment Cost)
    C -- If Multiple Parts --> C5(Non-Editable & Message)

    B -- True --> D[Single Parts Table (Itemized View)]
    D -- Rows --> D1[Part 1 Row: "Other Work"]
    D1 -- Columns --> D1A(Part Name)
    D1 -- Columns --> D1B(Time Hours)
    D1 -- Columns --> D1C(Time Cost)
    D1 -- Columns --> D1D(Material Cost)
    D1 -- Columns --> D1E(Adjustment Cost)
    D -- Rows --> D2[Part 2 Row: "Custom Part A"]
    D2 -- Columns --> D2A(Part Name)
    D2 -- Columns --> D2B(Time Hours)
    D2 -- Columns --> D2C(Time Cost)
    D2 -- Columns --> D2D(Material Cost)
    D2 -- Columns --> D2E(Adjustment Cost)
    D --> D3[Add/Edit/Delete Part Controls (via row operations)]
```

### Ticket 6: Implement Readonly Tables for Linked Quotes
**Goal**: Make appropriate tables readonly when a job has a linked quote.

1. Update the UI to detect when a job has a linked quote
2. Make the relevant tables readonly in this case
3. Add visual indicators to show which tables are readonly
4. Add explanatory tooltips

**Technical Details**:
- Add a check in the JavaScript to detect linked quotes
- Modify the grid options to set editable=false when appropriate
- Add CSS classes for visual indication of readonly status
- Add tooltips explaining why tables are readonly

**Now Test**: Create a job with a linked quote and verify the appropriate tables become readonly.

### Ticket 7: Google Sheets Data Synchronization
**Goal**: Implement two-way synchronization between the job and the linked quote spreadsheet.

1. Create service methods to read data from the linked spreadsheet
2. Implement logic to map spreadsheet data to job parts and entries
3. Add functionality to update the spreadsheet when job data changes
4. Add a manual sync button and automatic sync on save

**Technical Details**:
- Define a clear mapping between spreadsheet structure and job data
- Implement bidirectional synchronization in the Google Sheets service
- Add a "Sync with Spreadsheet" button to the job edit page
- Add hooks in the autosave functionality to update the spreadsheet

**Now Test**: Make changes in the job and verify they appear in the spreadsheet; make changes in the spreadsheet and verify they appear in the job.

### Ticket 8: Timesheet Entry Integration with Parts
**Goal**: Ensure timesheet entries work correctly with the new parts structure.

1. Update the timesheet entry UI to select which part the time belongs to
2. Modify the timesheet entry saving logic to associate entries with parts
3. Update the job reality section to display timesheet entries by part

**Technical Details**:
- Modify the TimeEntry model to reference a Part instead of directly referencing JobPricing
- Update the timesheet entry form to include a part selection dropdown
- Modify the timesheet serializer to handle the part reference
- Update the job reality section to group entries by part

**Now Test**: Add timesheet entries to different parts and verify they appear correctly in the job reality section.

### Ticket 9: Stock Addition Integration with Parts
**Goal**: Ensure adding stock to jobs works with the parts structure.

1. Update the "Add Stock" functionality to associate stock with specific parts
2. Modify the stock usage UI to select which part the stock belongs to
3. Update the job reality section to display stock by part

**Technical Details**:
- Modify the MaterialEntry model to reference a Part
- Update the stock usage UI to include a part selection
- Modify the stock usage service to handle part references
- Update the job reality section to display stock items grouped by part

**Now Test**: Add stock to different parts and verify it appears correctly in the job reality section.

### Ticket 10: Final Testing and Documentation
**Goal**: Ensure the entire system works correctly and is well-documented.

1. Create comprehensive documentation for the new features
2. Add tooltips and help text throughout the UI
3. Perform thorough testing of all functionality
4. Fix any remaining issues

**Technical Details**:
- Update user documentation with instructions for linked quotes and parts
- Add developer documentation explaining the data model and synchronization
- Create test cases covering all aspects of the new functionality
- Perform end-to-end testing of the entire job lifecycle

**Now Test**: Perform end-to-end testing of the entire job lifecycle with linked quotes and parts.

### Ticket 11: Shift to remove the old Gemini API Key

We need to use Service accounts as screated in the earlier steps.


genai.configure(credentials=creds)

model = genai.GenerativeModel("gemini-2.5-pro-exp-03-25")
response = model.generate_content("Summarise: 5 tips for running a good stand-up meeting.")

print(response.text)


## Potential Risks and Mitigations

1. **Data Migration Complexity**:
   - Risk: Migrating existing jobs to the new parts structure could be complex
   - Mitigation: Create a thorough data migration plan and test extensively with production data copies

2. **Google Sheets API Limitations**:
   - Risk: API rate limits or performance issues
   - Mitigation: Implement caching, batch operations, and error handling

3. **UI Complexity**:
   - Risk: The UI could become too complex with the addition of parts
   - Mitigation: Focus on usability, add clear documentation, and gather user feedback early

4. **Synchronization Conflicts**:
   - Risk: Conflicts between spreadsheet changes and job changes
   - Mitigation: Implement conflict detection and resolution strategies

## Conclusion

This implementation plan breaks down the linked quote feature into manageable tickets that can be implemented and tested incrementally. Each ticket builds on the previous one, ensuring that the system remains stable throughout the implementation process.

By following this plan, we can successfully implement the linked quote feature while minimizing disruption to existing functionality and ensuring a smooth transition for users.
