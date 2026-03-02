# Process Documents - Frontend Spec

## Overview

The backend `SafetyDocument` model has been renamed to `ProcessDocument` with expanded functionality. The frontend needs a new **Process Documents** section that replaces the current Safety Documents UI, providing a browsable library of company process documents (SOPs, policies, forms, registers, references).

Existing JSA/SWP/SOP functionality should continue to work — it's now a subset of the broader Process Documents system.

## API Changes

### New endpoints

```
GET    /rest/process-documents/                    # list with filters
GET    /rest/process-documents/<id>/               # detail
POST   /rest/process-documents/                    # create new document
PUT    /rest/process-documents/<id>/               # update metadata
DELETE /rest/process-documents/<id>/               # delete
GET    /rest/process-documents/<id>/content/       # read Google Docs content
PUT    /rest/process-documents/<id>/content/       # update Google Docs content
POST   /rest/process-documents/<id>/fill/          # create record from template
POST   /rest/process-documents/<id>/complete/      # mark as completed (read-only)
```

### Query parameters for list endpoint

- `?type=procedure` — filter by document_type (procedure/form/register/reference)
- `?tags=safety,machinery` — filter by tags (comma-separated, all must match)
- `?status=active` — filter by status (draft/active/completed/archived)
- `?is_template=true` — filter templates only
- `?q=drill+press` — search title and document_number

### Response shape (list)

```json
{
  "id": "uuid",
  "document_type": "procedure",
  "document_number": "355",
  "title": "Drill Press Safe Operating Procedure",
  "tags": ["safety", "sop", "machinery"],
  "is_template": false,
  "status": "active",
  "google_doc_url": "https://docs.google.com/document/d/.../edit",
  "job_number": null,
  "created_at": "2026-03-03T10:00:00Z",
  "updated_at": "2026-03-03T10:00:00Z",
  "site_location": ""
}
```

### Response shape (detail — adds these fields)

```json
{
  "...all list fields...",
  "job_id": null,
  "company_name": "Morris Sheetmetal",
  "google_doc_id": "1abc...",
  "parent_template_id": null
}
```

### Fill endpoint (POST /rest/process-documents/<id>/fill/)

Request:
```json
{
  "job_id": "uuid-or-null"
}
```

Response: full detail shape of the newly created record (status="draft").

### Complete endpoint (POST /rest/process-documents/<id>/complete/)

No request body. Response: full detail shape with status="completed".

## Existing endpoints preserved

These still work and return the same data (now filtered by tags internally):

```
GET  /rest/jobs/<job_id>/jsa/
POST /rest/jobs/<job_id>/jsa/generate/
GET  /rest/swp/
POST /rest/swp/generate/
GET  /rest/sop/
POST /rest/sop/generate/
```

The existing Safety Wizard, JSA generation, SWP generation, and SOP generation UIs continue to work unchanged.

## Pages to build

### 1. Process Documents Library (`/process-documents`)

A browsable library of all process documents. This is the main entry point.

**Layout:**
- Top: page title "Process Documents", search bar, "New Document" button
- Below search: filter chips/pills for document type and common tags
- Main area: table/list of documents

**Filters:**
- Type pills: All | Procedures | Forms | Registers | References
- Tag pills: dynamically generated from available tags (safety, machinery, handtool, training, etc.)
- Status dropdown: Active (default) | Draft | Completed | Archived | All
- Templates toggle: "Show templates only"
- Search: filters on title and document_number

**Table columns:**
- Doc # (document_number, e.g. "355")
- Title
- Type (badge/chip: procedure/form/register/reference)
- Tags (small chips)
- Status (badge: active/draft/completed/archived)
- Template indicator (icon if is_template)
- Updated (relative date)
- Actions: Open in Google Docs (external link icon), Fill (if template), Complete (if draft)

**Row click:** Opens document detail view.

**"New Document" button:** Opens a simple form modal:
- Title (required)
- Document number (optional)
- Type dropdown (procedure/form/register/reference)
- Tags input (free text, comma-separated or tag chips)
- Is template checkbox
- Submit → POST to `/rest/process-documents/`

### 2. Process Document Detail (`/process-documents/:id`)

**Layout:**
- Header: title, document number badge, type badge, status badge
- Metadata section: created date, updated date, company, site location, linked job (if any)
- Tags: editable tag chips
- If template: "Fill in this form" button (prominent)
- If draft: "Mark as completed" button
- If has google_doc_url: "Open in Google Docs" button (external link)
- If has parent_template: link back to the template

**Completed records section (if template):**
- List of records created from this template (via parent_template)
- Table with: date created, status, linked job, link to record

### 3. Navigation

Add "Process Documents" to the main navigation sidebar/menu. It should sit near the existing Safety items or replace them.

The existing `/safety/jsa` and `/safety/swp` routes can remain as they are — they're still useful as filtered views. Optionally, they could become links that navigate to `/process-documents?tags=jsa` and `/process-documents?tags=swp`.

## Types to update

```typescript
// New/updated types

type ProcessDocumentType = 'procedure' | 'form' | 'register' | 'reference'
type ProcessDocumentStatus = 'draft' | 'active' | 'completed' | 'archived'

interface ProcessDocument {
  id: string
  document_type: ProcessDocumentType
  document_number: string
  title: string
  tags: string[]
  is_template: boolean
  status: ProcessDocumentStatus
  google_doc_id: string
  google_doc_url: string
  parent_template_id: string | null
  job_id: string | null
  job_number: string | null
  company_name: string
  site_location: string
  created_at: string
  updated_at: string
}

interface ProcessDocumentList {
  id: string
  document_type: ProcessDocumentType
  document_number: string
  title: string
  tags: string[]
  is_template: boolean
  status: ProcessDocumentStatus
  google_doc_url: string
  job_number: string | null
  site_location: string
  created_at: string
  updated_at: string
}
```

## Store updates

The existing `safetyDocuments` store can be extended or a new `processDocuments` store created. A new store is cleaner:

```typescript
// stores/processDocuments.ts

state: {
  documents: ProcessDocumentList[]
  currentDocument: ProcessDocument | null
  isLoading: boolean
  error: string | null
  filters: {
    type: ProcessDocumentType | null
    tags: string[]
    status: ProcessDocumentStatus | 'all'
    isTemplate: boolean | null
    search: string
  }
}

actions: {
  loadDocuments()           // GET /rest/process-documents/ with current filters
  loadDocument(id)          // GET /rest/process-documents/<id>/
  createDocument(data)      // POST /rest/process-documents/
  updateDocument(id, data)  // PUT /rest/process-documents/<id>/
  deleteDocument(id)        // DELETE /rest/process-documents/<id>/
  fillTemplate(id, jobId?)  // POST /rest/process-documents/<id>/fill/
  completeDocument(id)      // POST /rest/process-documents/<id>/complete/
  setFilters(filters)       // Update filters and reload
}
```

## Notes

- The existing Safety Wizard modal and AI generation features continue to work unchanged — they create ProcessDocuments with appropriate tags
- Google Docs links should open in a new tab
- The "Fill in this form" action creates a copy and navigates to the new record's detail page
- Tag filtering should feel fast — consider debouncing search input
- Document numbers sort numerically, not alphabetically (e.g. "3" before "100")
