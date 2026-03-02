# Process Documents Migration Design

## Goal

Replace the Dropbox `Health & Safety` folder with an in-app document management system. Rename `SafetyDocument` to `ProcessDocument` to reflect broader scope. Migrate ~80 living numbered documents (Doc.100–Doc.450) into the app.

All documents start as Google Docs. Over time, structured forms/registers get replaced by custom app UIs with database-backed entries.

## Current State

### Existing `SafetyDocument` model
- Supports three types: `jsa`, `swp`, `sop`
- Content lives in Google Docs (model stores `google_doc_id` + `google_doc_url`)
- AI generation via `SafetyAIService` (hazards, controls, full documents)
- JSAs link to jobs; SWPs/SOPs are standalone
- No version history in DB (Google Docs handles versioning)

### Dropbox folder (`dropbox/Health & Safety/`)
- ~80 numbered living documents (Doc.100–Doc.450)
- Historical completed records (inspections, training, incidents)
- External references (SDS sheets, regulatory guides)
- Photos, CAD files, signs (non-document assets)

## Design

### Model: `ProcessDocument` (replaces `SafetyDocument`)

```python
class ProcessDocument(models.Model):
    id = UUIDField(primary_key=True)

    # Classification
    document_type = CharField(choices=[
        ("procedure", "Procedure"),   # SOPs, SWPs, policies, emergency procedures
        ("form", "Form"),             # Templates that get filled in
        ("register", "Register"),     # Ongoing logs with line entries
        ("reference", "Reference"),   # External/planning docs
    ])
    tags = JSONField(default=list)  # Free-text tags, e.g. ["safety", "machinery", "sop", "policy"]

    # Identity
    title = CharField(max_length=255)
    document_number = CharField(max_length=20, blank=True)  # "100", "350", etc.

    # Google Docs (populated for prose docs; blank when content moves to app forms)
    google_doc_id = CharField(max_length=255, blank=True)
    google_doc_url = URLField(blank=True)

    # Template/record workflow
    is_template = BooleanField(default=False)
    status = CharField(choices=[
        ("draft", "Draft"),
        ("active", "Active"),
        ("completed", "Completed"),
        ("archived", "Archived"),
    ], default="active")
    parent_template = ForeignKey("self", null=True, blank=True, on_delete=SET_NULL,
                                  related_name="completed_records")

    # Existing relationships
    job = ForeignKey("Job", null=True, blank=True, on_delete=SET_NULL,
                     related_name="process_documents")
    company_name = CharField(max_length=255, blank=True)
    site_location = CharField(max_length=255, blank=True)

    # Timestamps
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

### Content backends

Documents have two possible content backends. All start as Google Docs; some migrate to app forms over time.

| Content backend | `document_type` | Editing | `google_doc_id` |
|----------------|-----------------|---------|-----------------|
| **Google Docs** | `procedure`, `reference` | Click through to Google Docs | Populated |
| **Database entries** | `form`, `register` (future) | App forms in the UI | Blank |

The migration path for any document:
1. Dropbox `.doc` file → **Google Doc** (all documents, day one)
2. Some Google Docs later replaced by **app forms** (as we build custom UIs)

### Generic entry model (for structured forms)

```python
class ProcessDocumentEntry(models.Model):
    id = UUIDField(primary_key=True)
    document = ForeignKey(ProcessDocument, related_name="entries", on_delete=CASCADE)
    entry_date = DateField()
    entered_by = ForeignKey(Staff, null=True, on_delete=SET_NULL)
    data = JSONField()  # Schema varies by document type
    created_at = DateTimeField(auto_now_add=True)
```

Specific models (e.g. `MaintenanceLogEntry`) created only when strong querying/reporting is needed. The generic model handles most cases.

### Backward compatibility for JSA/SWP/SOP

The existing JSA/SWP/SOP workflow continues to work:
- **JSA** → `ProcessDocument(document_type="form", tags=["safety", "jsa"], job=job)`
- **SWP** → `ProcessDocument(document_type="procedure", tags=["safety", "swp"])`
- **SOP** → `ProcessDocument(document_type="procedure", tags=["sop"])`

Existing API endpoints preserved via tag filtering.

### Template → Completed Record Flow

1. User views a template document (e.g. Doc.110 Ladder Inspection Checklist)
2. User clicks "Fill in this form"
3. For Google Docs-backed forms: copies the Google Doc
4. For app-backed forms: creates new `ProcessDocument` with `parent_template` FK
5. New record has `is_template=False`, `status="draft"`, optionally linked to a `job`
6. User fills it in (Google Docs or app form)
7. User marks complete → `status="completed"` (Google Doc set to read-only if applicable)

### Document type mapping from Dropbox

| Doc # Range | Category | `document_type` | Tags |
|-------------|----------|------------------|------|
| 100–101 | H&S policy/statement | `procedure` | `["safety", "policy"]` |
| 102–106 | Planning docs | `reference` | `["safety", "planning"]` |
| 107–119 | Inspection forms | `form` | `["safety", "inspection"]` |
| 120 | Induction kit | `form` | `["training", "induction"]` |
| 150–173 | Machine inspection | `form` | `["safety", "inspection", "machinery"]` |
| 200–206 | Incident management | `form` or `procedure` | `["safety", "incident"]` |
| 250–259 | Training forms | `form` | `["training"]` |
| 300–310 | Hand tool SOPs | `procedure` | `["safety", "sop", "handtool"]` |
| 350–375 | Machinery SOPs | `procedure` | `["safety", "sop", "machinery"]` |
| 380 | Hazard register | `register` | `["safety", "hazard"]` |
| 400–405 | Emergency/general | `procedure` or `form` | `["safety", "emergency"]` |
| 415–420 | Meeting forms | `form` | `["administration", "meeting"]` |
| 450 | Air compressor SOP | `procedure` | `["safety", "sop", "machinery"]` |

### Migration strategy

1. **Rename model** — `SafetyDocument` → `ProcessDocument`, add new fields via Django migration. Map existing `jsa`/`swp`/`sop` types to new types + tags.
2. **Upload Dropbox docs to Google Drive** — `.doc`/`.docx` files upload via Drive API (auto-converts to Google Docs format). PDFs upload as-is.
3. **Create `ProcessDocument` records** — One per living document, with metadata from the numbering system.
4. **Mark templates** — Forms meant to be filled in get `is_template=True`.

### Out of scope

- Migrating historical completed records (old inspections, training records)
- SDS sheets (external supplier documents)
- Photos, CAD files, signs (non-document assets)
- AI generation for document types beyond JSA/SWP/SOP
- Custom app forms for specific document types (future, incremental)

### API endpoints

```
# Existing (preserved via tag filtering)
GET  /rest/jobs/<job_id>/jsa/
POST /rest/jobs/<job_id>/jsa/generate/
GET  /rest/swp/
POST /rest/swp/generate/
GET  /rest/sop/
POST /rest/sop/generate/

# New general endpoints
GET    /rest/process-documents/                    # list with type/tag/status filters
GET    /rest/process-documents/<id>/               # detail
POST   /rest/process-documents/                    # create new
PUT    /rest/process-documents/<id>/               # update metadata
DELETE /rest/process-documents/<id>/               # delete
GET    /rest/process-documents/<id>/content/       # read from Google Docs
PUT    /rest/process-documents/<id>/content/       # update in Google Docs
POST   /rest/process-documents/<id>/fill/          # create record from template
POST   /rest/process-documents/<id>/complete/      # mark completed

# AI endpoints (unchanged)
POST /rest/safety-ai/generate-hazards/
POST /rest/safety-ai/generate-controls/
POST /rest/safety-ai/improve-section/
POST /rest/safety-ai/improve-document/
```

### File changes

| File | Action |
|------|--------|
| `apps/job/models/safety_document.py` | Rename to `process_document.py`, rename model, add fields |
| `apps/job/models/__init__.py` | Regenerate |
| `apps/job/serializers/safety_document_serializer.py` | Rename, update for new fields |
| `apps/job/views/safety_viewsets.py` | Rename, add new endpoints |
| `apps/job/services/safety_document_service.py` | Rename, add fill/complete methods |
| `apps/job/services/google_docs_service.py` | Add `copy_document`, `set_readonly` methods |
| `apps/job/urls_rest.py` | Add new routes |
| `apps/job/migrations/` | New migration for rename + new fields |
| New management command | Bulk-import Dropbox documents to Google Drive + create records |
