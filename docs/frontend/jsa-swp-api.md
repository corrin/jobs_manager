# JSA/SWP Generation - Frontend Integration Guide

This document describes the backend API for AI-powered Job Safety Analysis (JSA) and Safe Work Procedure (SWP) generation.

## Overview

The system supports two document types:
- **JSA (Job Safety Analysis)**: Generated from a job, linked to that job for context, but persists as a reference document
- **SWP (Safe Work Procedure)**: Standalone documents, not linked to any job

Both follow a **draft → final** workflow where documents can be edited before being finalized as PDF.

---

## Data Model

### SafetyDocument

```typescript
interface SafetyDocument {
  id: string;  // UUID
  document_type: 'jsa' | 'swp';
  job?: string;  // UUID, only for JSA
  status: 'draft' | 'final';

  title: string;
  site_location: string;
  description: string;
  ppe_requirements: string[];
  tasks: Task[];
  additional_notes: string;

  pdf_file_path?: string;  // Set after finalization
  created_at: string;  // ISO datetime
  updated_at: string;  // ISO datetime
}

interface Task {
  step_number: number;
  description: string;
  summary: string;  // 1-3 word summary
  potential_hazards: string[];
  initial_risk_rating: 'Low' | 'Moderate' | 'High' | 'Extreme';
  control_measures: ControlMeasure[];
  revised_risk_rating: 'Low' | 'Moderate' | 'High' | 'Extreme';
}

interface ControlMeasure {
  measure: string;
  associated_hazard: string;
}
```

---

## API Endpoints

### JSA (Job-Linked)

#### Generate JSA for a Job
```
POST /api/rest/jobs/{job_id}/jsa/generate/
```
Generates a new draft JSA using AI with job context. Returns the created SafetyDocument.

**Response**: `201 Created` with SafetyDocument

#### List JSAs for a Job
```
GET /api/rest/jobs/{job_id}/jsa/
```
Returns all JSAs linked to this job.

**Response**: `200 OK` with list of SafetyDocument

---

### SWP (Standalone)

#### Generate SWP
```
POST /api/rest/swp/generate/
```
Generates a new draft SWP using AI (no job context).

**Request Body**:
```json
{
  "title": "Safe Work Procedure for Hot Work",
  "description": "Procedure for welding and grinding operations in workshop",
  "site_location": "Main Workshop"  // optional
}
```

**Response**: `201 Created` with SafetyDocument

#### List All SWPs
```
GET /api/rest/swp/
```
Returns all SWPs (paginated).

**Response**: `200 OK` with list of SafetyDocument

---

### Shared Document Management

#### List All Safety Documents
```
GET /api/rest/safety-documents/
```
Returns all safety documents (JSAs + SWPs), optionally filtered.

**Query Parameters**:
- `document_type`: Filter by `jsa` or `swp`
- `status`: Filter by `draft` or `final`
- `search`: Search in title/description

#### Get Document Details
```
GET /api/rest/safety-documents/{doc_id}/
```
Returns full document with all tasks and controls.

#### Update Document (Draft Only)
```
PUT /api/rest/safety-documents/{doc_id}/
PATCH /api/rest/safety-documents/{doc_id}/
```
Update a draft document. PUT replaces entirely, PATCH does partial update.

**Note**: Cannot update finalized documents.

#### Delete Document
```
DELETE /api/rest/safety-documents/{doc_id}/
```
Delete a document. Returns `204 No Content`.

---

### AI-Assisted Editing

#### Generate Hazards for Task
```
POST /api/rest/safety-documents/{doc_id}/tasks/{task_num}/generate-hazards/
```
AI-generates potential hazards for a specific task.

**Request Body**:
```json
{
  "task_description": "Set up scaffolding at height"
}
```

**Response**:
```json
{
  "hazards": [
    "Fall from height",
    "Falling objects",
    "Unstable scaffolding",
    "Weather exposure"
  ]
}
```

#### Generate Controls for Hazards
```
POST /api/rest/safety-documents/{doc_id}/tasks/{task_num}/generate-controls/
```
AI-generates control measures for specified hazards.

**Request Body**:
```json
{
  "hazards": ["Fall from height", "Falling objects"]
}
```

**Response**:
```json
{
  "controls": [
    {"measure": "Install guardrails on all open edges", "associated_hazard": "Fall from height"},
    {"measure": "Use safety harness when working above 2m", "associated_hazard": "Fall from height"},
    {"measure": "Establish exclusion zone below work area", "associated_hazard": "Falling objects"},
    {"measure": "Secure all tools and materials", "associated_hazard": "Falling objects"}
  ]
}
```

---

### PDF Generation & Finalization

#### Finalize Document
```
POST /api/rest/safety-documents/{doc_id}/finalize/
```
Generates PDF and marks document as final. Document can no longer be edited.

**Response**: `200 OK` with updated SafetyDocument (includes `pdf_file_path`)

#### Download PDF
```
GET /api/rest/safety-documents/{doc_id}/pdf/
```
Returns the generated PDF file.

**Response**: `200 OK` with `Content-Type: application/pdf`

**Note**: Only available after finalization.

---

## Workflow

### Creating a JSA

1. **Generate**: `POST /api/rest/jobs/{job_id}/jsa/generate/`
   - AI generates initial content based on job description
   - Returns draft document

2. **Edit** (optional): `PATCH /api/rest/safety-documents/{doc_id}/`
   - User reviews and edits tasks, hazards, controls
   - Can use AI helpers to generate hazards/controls

3. **Finalize**: `POST /api/rest/safety-documents/{doc_id}/finalize/`
   - Generates PDF
   - Document becomes read-only

4. **Download**: `GET /api/rest/safety-documents/{doc_id}/pdf/`
   - Download the generated PDF

### Creating a SWP

Same workflow but starts with:
1. **Generate**: `POST /api/rest/swp/generate/` with title/description

---

## UI Recommendations

### JSA Section (on Job Detail Page)
- List existing JSAs for the job
- "Generate JSA" button → shows loading while AI generates
- Click JSA to view/edit (if draft) or view (if final)

### SWP Section (standalone page)
- List all SWPs with search/filter
- "Create SWP" button → form for title/description → generates
- Click SWP to view/edit/finalize

### Document Editor
- Display tasks in numbered steps
- Each task shows:
  - Description (editable)
  - Hazards (list, with "Generate More" button)
  - Controls (list with associated hazard, "Generate Controls" button)
  - Risk ratings (dropdown: Low/Moderate/High/Extreme)
- PPE section (checkbox or tag list)
- Site location, additional notes

### Risk Rating Colors
- **Low**: Green
- **Moderate**: Orange/Yellow
- **High**: Red
- **Extreme**: Dark Red

---

## Error Handling

| Status | Meaning |
|--------|---------|
| 400 | Invalid request data |
| 404 | Document or job not found |
| 409 | Cannot edit finalized document |
| 500 | AI generation failed (rare) |

Error responses include:
```json
{
  "error": "Cannot modify a finalized document"
}
```
