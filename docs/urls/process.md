# Process URLs Documentation

<!-- This file is auto-generated. To regenerate, run: python scripts/generate_url_docs.py -->

### Rest Management
| URL Pattern | View | Name | Description |
|-------------|------|------|-------------|
| `/rest/forms/<str:category>/<uuid:pk>/complete/` | `process_document_viewsets.ProcessDocumentCompleteView` | `process:form_complete` | Mark a document as completed (read-only). |
| `/rest/forms/<str:category>/<uuid:pk>/fill/` | `process_document_viewsets.ProcessDocumentFillView` | `process:form_fill` | Create a new record from a template. |
| `/rest/jobs/<uuid:job_id>/jsa/` | `process_document_viewsets.JSAListView` | `process:jsa_list` | List all JSAs for a job. |
| `/rest/jobs/<uuid:job_id>/jsa/generate/` | `process_document_viewsets.JSAGenerateView` | `process:jsa_generate` | Generate a new JSA for a job. |
| `/rest/procedures/<str:category>/<uuid:pk>/content/` | `process_document_viewsets.ProcessDocumentContentView` | `process:procedure_content` | GET/PUT content for a process document stored in Google Docs. |
| `/rest/procedures/safety/generate-sop/` | `process_document_viewsets.SOPGenerateView` | `process:sop_generate` | Generate a new Standard Operating Procedure. |
| `/rest/procedures/safety/generate-swp/` | `process_document_viewsets.SWPGenerateView` | `process:swp_generate` | Generate a new Safe Work Procedure. |
| `/rest/safety-ai/generate-controls/` | `process_document_viewsets.AIGenerateControlsView` | `process:ai_generate_controls` | Generate controls for hazards using AI. |
| `/rest/safety-ai/generate-hazards/` | `process_document_viewsets.AIGenerateHazardsView` | `process:ai_generate_hazards` | Generate hazards for a task description using AI. |
| `/rest/safety-ai/improve-document/` | `process_document_viewsets.AIImproveDocumentView` | `process:ai_improve_document` | Improve an entire document using AI. |
| `/rest/safety-ai/improve-section/` | `process_document_viewsets.AIImproveSectionView` | `process:ai_improve_section` | Improve a section of text using AI. |
