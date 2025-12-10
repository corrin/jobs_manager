# JSA/SWP Safety Documents - Frontend Integration Guide

This document describes the backend API for AI-powered Job Safety Analysis (JSA) and Safe Work Procedure (SWP) generation and editing.

## Overview

The system supports two document types:
- **JSA (Job Safety Analysis)**: Generated from a job, linked to that job for context
- **SWP (Safe Work Procedure)**: Standalone documents, not linked to any job (same as SOP - Safe Operating Procedure)

### Key Architecture

**Documents are stored and edited in Google Docs.** The backend:
1. Uses AI to generate safety document content
2. Creates a formatted Google Doc with the content
3. Returns a Google Docs URL for viewing/editing
4. Provides APIs to read/write content for wizard-style editing
5. Provides granular AI endpoints for improving specific sections

### Workflow Options

**Simple flow** (for quick generation):
1. Generate document with AI
2. Open in Google Docs for manual editing

**Wizard flow** (for guided improvement):
1. Open existing document OR generate new one
2. Read content from Google Doc
3. Step through wizard, using AI to improve each section
4. Write improved content back to Google Doc

---

## Data Model

### SafetyDocument (metadata)

```typescript
interface SafetyDocument {
  id: string;                    // UUID
  document_type: 'jsa' | 'swp';

  // Job link (JSA only)
  job_id?: string;               // UUID, null for SWP
  job_number?: string;           // e.g., "J1234", null for SWP

  // Metadata
  title: string;
  company_name: string;
  site_location: string;

  // Google Docs reference
  google_doc_id: string;         // Google Docs document ID
  google_doc_url: string;        // URL to edit in Google Docs

  // Timestamps
  created_at: string;            // ISO datetime
  updated_at: string;            // ISO datetime
}
```

### SafetyDocumentContent (full content)

```typescript
interface SafetyDocumentContent {
  title: string;
  document_type: 'jsa' | 'swp';
  description: string;
  site_location: string;
  ppe_requirements: string[];
  tasks: Task[];
  additional_notes: string;
  raw_text: string;              // Full document text for AI processing
}

interface Task {
  step_number: number;
  description: string;
  summary: string;
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

### Document Generation

#### Generate JSA for a Job
```
POST /api/rest/jobs/{job_id}/jsa/generate/
```

Generates a new JSA using AI based on job context, creates a formatted Google Doc.

**Request Body**: None required

**Response**: `201 Created` with SafetyDocument

#### Generate SWP
```
POST /api/rest/swp/generate/
```

Generates a new SWP using AI.

**Request Body**:
```json
{
  "title": "Welding Operations",
  "description": "Standard procedure for MIG/TIG welding",
  "site_location": "Main Workshop"
}
```

**Response**: `201 Created` with SafetyDocument

---

### Document Management

#### List All Safety Documents
```
GET /api/rest/safety-documents/
```

**Query Parameters**:
- `type`: Filter by `jsa` or `swp`
- `q`: Search by title

**Response**: `200 OK` with array of SafetyDocument

#### Get Document Details
```
GET /api/rest/safety-documents/{doc_id}/
```

**Response**: `200 OK` with SafetyDocument

#### Delete Document
```
DELETE /api/rest/safety-documents/{doc_id}/
```

**Response**: `204 No Content`

---

### Content Read/Write (for wizard flow)

#### Read Content from Google Doc
```
GET /api/rest/safety-documents/{doc_id}/content/
```

Reads and parses content from the document's Google Doc.

**Response**: `200 OK`
```json
{
  "title": "Welding Operations",
  "document_type": "swp",
  "description": "Standard procedure for...",
  "site_location": "Main Workshop",
  "ppe_requirements": ["Safety glasses", "Welding helmet", ...],
  "tasks": [...],
  "additional_notes": "...",
  "raw_text": "Full document text..."
}
```

#### Update Google Doc Content
```
PUT /api/rest/safety-documents/{doc_id}/content/
```

Replaces the Google Doc content with new content.

**Request Body**:
```json
{
  "title": "Welding Operations",
  "description": "Improved description...",
  "site_location": "Main Workshop",
  "ppe_requirements": ["Safety glasses", "Welding helmet", ...],
  "tasks": [
    {
      "step_number": 1,
      "description": "Set up welding equipment",
      "summary": "Setup",
      "potential_hazards": ["Electric shock", "Fire"],
      "initial_risk_rating": "High",
      "control_measures": [
        {"measure": "Check equipment grounding", "associated_hazard": "Electric shock"}
      ],
      "revised_risk_rating": "Low"
    }
  ],
  "additional_notes": "..."
}
```

**Response**: `200 OK` with updated SafetyDocument

---

### AI Endpoints (for wizard steps)

#### Generate Hazards
```
POST /api/rest/safety-ai/generate-hazards/
```

AI generates potential hazards for a task.

**Request Body**:
```json
{
  "task_description": "Set up scaffolding at height for installation work"
}
```

**Response**: `200 OK`
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

#### Generate Controls
```
POST /api/rest/safety-ai/generate-controls/
```

AI generates control measures for hazards.

**Request Body**:
```json
{
  "hazards": ["Fall from height", "Falling objects"],
  "task_description": "Working on scaffolding"
}
```

**Response**: `200 OK`
```json
{
  "controls": [
    {"measure": "Install guardrails on all open edges", "associated_hazard": "Fall from height"},
    {"measure": "Use safety harness when above 2m", "associated_hazard": "Fall from height"},
    {"measure": "Establish exclusion zone below", "associated_hazard": "Falling objects"},
    {"measure": "Secure all tools and materials", "associated_hazard": "Falling objects"}
  ]
}
```

#### Improve Section
```
POST /api/rest/safety-ai/improve-section/
```

AI improves a specific section of text.

**Request Body**:
```json
{
  "section_text": "Wear gloves",
  "section_type": "ppe",
  "context": "Welding operations"
}
```

**Response**: `200 OK`
```json
{
  "improved_text": "Wear appropriate welding gloves (leather or heat-resistant) rated for the type of welding being performed. Replace gloves when worn or damaged."
}
```

#### Improve Entire Document
```
POST /api/rest/safety-ai/improve-document/
```

AI analyzes and improves an entire document.

**Request Body**:
```json
{
  "raw_text": "Full document text...",
  "document_type": "swp"
}
```

**Response**: `200 OK` with full SafetyDocumentContent structure (improved)

---

## Wizard Flow Implementation

### Step-by-Step Guide

```
┌─────────────────────────────────────────────────────────────────┐
│  1. User selects "Edit with AI" on existing document            │
│     OR creates new document                                     │
│                           ↓                                     │
│  2. GET /safety-documents/{id}/content/                        │
│     → Load current content into wizard state                    │
│                           ↓                                     │
│  3. WIZARD STEP: Review Description                             │
│     → POST /safety-ai/improve-section/ (section_type: desc)     │
│     → User reviews/accepts improvements                         │
│                           ↓                                     │
│  4. WIZARD STEP: Review Tasks & Hazards                         │
│     → For each task: POST /safety-ai/generate-hazards/          │
│     → User adds/removes hazards                                 │
│                           ↓                                     │
│  5. WIZARD STEP: Review Controls                                │
│     → POST /safety-ai/generate-controls/                        │
│     → User reviews control measures                             │
│                           ↓                                     │
│  6. WIZARD STEP: Review PPE                                     │
│     → POST /safety-ai/improve-section/ (section_type: ppe)      │
│                           ↓                                     │
│  7. WIZARD STEP: Final Review                                   │
│     → Show complete document preview                            │
│                           ↓                                     │
│  8. PUT /safety-documents/{id}/content/                        │
│     → Save improved content back to Google Doc                  │
└─────────────────────────────────────────────────────────────────┘
```

### Frontend State Management

```typescript
interface WizardState {
  documentId: string;
  currentStep: number;
  content: SafetyDocumentContent;
  originalContent: SafetyDocumentContent;  // For comparison
  isDirty: boolean;
}

const WIZARD_STEPS = [
  'description',
  'tasks',
  'hazards',
  'controls',
  'ppe',
  'review'
];
```

---

## UI Recommendations

### JSA on Job Detail Page

```
┌─────────────────────────────────────────────────────────┐
│ Job Safety Analysis                                      │
├─────────────────────────────────────────────────────────┤
│ [Generate New JSA]                                       │
│                                                          │
│ Existing JSAs:                                          │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ JSA - Steel Staircase Installation                  │ │
│ │ Created: 9 Dec 2025                                 │ │
│ │ [View in Google Docs] [Edit with AI Wizard]        │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### SWP/SOP Management Page

```
┌─────────────────────────────────────────────────────────┐
│ Safe Work Procedures                   [Create New SWP]  │
├─────────────────────────────────────────────────────────┤
│ Search: [________________]                              │
├─────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Welding Operations                                  │ │
│ │ Main Workshop            Created: 5 Dec 2025        │ │
│ │ [View] [Edit with AI] [Delete]                      │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### AI Wizard Modal

```
┌─────────────────────────────────────────────────────────┐
│ Improve Safety Document                            [X]  │
├─────────────────────────────────────────────────────────┤
│ Step 2 of 6: Review Tasks & Hazards                     │
│ ━━━━━━━━━━━━━━━━━━━━━━░░░░░░░░░░░░░░░░░░░░             │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ Task 1: Set up welding equipment                        │
│                                                          │
│ Potential Hazards:                                      │
│ [✓] Electric shock                                      │
│ [✓] Fire hazard                                         │
│ [✓] UV radiation exposure                               │
│ [ ] Fume inhalation                    [AI suggested]   │
│                                                          │
│ [+ Add hazard manually]  [Generate more with AI]        │
│                                                          │
├─────────────────────────────────────────────────────────┤
│              [← Back]  [Skip]  [Next →]                 │
└─────────────────────────────────────────────────────────┘
```

---

## Error Handling

| Status | Meaning |
|--------|---------|
| 200 | Success |
| 201 | Document created |
| 204 | Deleted successfully |
| 400 | Invalid request data |
| 404 | Document not found |
| 500 | Server error (AI or Google API failure) |

**Error Response Format**:
```json
{
  "status": "error",
  "message": "Description of what went wrong"
}
```

---

## TypeScript API Client

```typescript
export const safetyApi = {
  // Document CRUD
  listDocuments: (type?: 'jsa' | 'swp'): Promise<SafetyDocument[]> =>
    api.get('/rest/safety-documents/', { params: { type } }),

  getDocument: (id: string): Promise<SafetyDocument> =>
    api.get(`/rest/safety-documents/${id}/`),

  deleteDocument: (id: string): Promise<void> =>
    api.delete(`/rest/safety-documents/${id}/`),

  // Generation
  generateJSA: (jobId: string): Promise<SafetyDocument> =>
    api.post(`/rest/jobs/${jobId}/jsa/generate/`),

  generateSWP: (data: SWPRequest): Promise<SafetyDocument> =>
    api.post('/rest/swp/generate/', data),

  // Content read/write
  getContent: (id: string): Promise<SafetyDocumentContent> =>
    api.get(`/rest/safety-documents/${id}/content/`),

  updateContent: (id: string, content: Partial<SafetyDocumentContent>): Promise<SafetyDocument> =>
    api.put(`/rest/safety-documents/${id}/content/`, content),

  // AI endpoints
  generateHazards: (taskDescription: string): Promise<{ hazards: string[] }> =>
    api.post('/rest/safety-ai/generate-hazards/', { task_description: taskDescription }),

  generateControls: (hazards: string[], taskDescription?: string): Promise<{ controls: ControlMeasure[] }> =>
    api.post('/rest/safety-ai/generate-controls/', { hazards, task_description: taskDescription }),

  improveSection: (sectionText: string, sectionType: string, context?: string): Promise<{ improved_text: string }> =>
    api.post('/rest/safety-ai/improve-section/', { section_text: sectionText, section_type: sectionType, context }),

  improveDocument: (rawText: string, documentType: 'jsa' | 'swp'): Promise<SafetyDocumentContent> =>
    api.post('/rest/safety-ai/improve-document/', { raw_text: rawText, document_type: documentType }),
};
```

---

## Summary of Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/rest/safety-documents/` | GET | List all documents |
| `/rest/safety-documents/{id}/` | GET | Get document metadata |
| `/rest/safety-documents/{id}/` | DELETE | Delete document |
| `/rest/safety-documents/{id}/content/` | GET | Read content from Google Doc |
| `/rest/safety-documents/{id}/content/` | PUT | Update Google Doc content |
| `/rest/jobs/{job_id}/jsa/` | GET | List JSAs for a job |
| `/rest/jobs/{job_id}/jsa/generate/` | POST | Generate new JSA |
| `/rest/swp/` | GET | List all SWPs |
| `/rest/swp/generate/` | POST | Generate new SWP |
| `/rest/safety-ai/generate-hazards/` | POST | AI generates hazards |
| `/rest/safety-ai/generate-controls/` | POST | AI generates controls |
| `/rest/safety-ai/improve-section/` | POST | AI improves a section |
| `/rest/safety-ai/improve-document/` | POST | AI improves entire document |
