# Xero Quote & Invoice Linking Plan

## Context

- When Jobs Manager is unavailable, finance staff can still raise quotes and invoices directly inside Xero.
- The current backend only supports *creating* quotes/invoices via `XeroQuoteManager` and `XeroInvoiceManager`; it has no pathway to ingest existing Xero documents and associate them with a job afterwards.
- Sync jobs populate `apps.accounting.models.Quote`/`Invoice`, but they leave `job_id` empty because there is no matching logic beyond the happy path where the document originated from the job itself.
- Operations need a first-class workflow to attach those pre-existing Xero documents to the correct job so downstream costing, events, and invoicing state remain accurate.

## Objectives

- Provide backend services + REST endpoints to link an existing Xero quote or invoice to a job by supplying a Xero document reference.
- Fetch the authoritative Xero payload, upsert local accounting records, and persist the `job` relationship inside a transaction.
- Guard against mismatched clients, duplicate links, or conflicting assignments and surface precise validation errors.
- Emit job events, refresh optimistic concurrency (`updated_at`), and re-run invoicing state checks so UI stays consistent.
- Produce documentation and API schema updates so the frontend can integrate safely.

## Non-Goals

- Frontend/UI work (handled in the Vue project).
- Bulk migration tooling for historical backfills (can follow once the single-link workflow exists).
- Automatic inference of job from arbitrary invoice metadata; the initial feature assumes a human provides the correct job.

## Constraints & Assumptions

- Xero URLs expose the document GUID; operators can copy either the GUID or the full URL. The backend should accept both forms.
- Quotes are one-to-one with jobs; linking a quote that is already attached to another job must raise a conflict unless explicitly overridden (no override in v1).
- Invoices can be many-to-one; however, an invoice already linked to a different job must be rejected.
- Jobs must own a client already synced to Xero (enforced during linking).
- Error handling must call `persist_app_error` before re-raising or returning a 4xx/5xx as per project guidelines.

## Architecture Direction

### Document Acquisition

- Add helper(s) that call the Accounting API to retrieve a quote or invoice by GUID. Allow optional filtering by document number if supplied.
- Reuse existing transformers (`transform_quote`, `transform_invoice`) to normalise and upsert the accounting models, ensuring `raw_json`, totals, and timestamps mirror the sync path.
- Parse user-provided references: strip whitespace, extract GUID from `https://go.xero.com/.../<uuid>` URLs, and validate UUID format early.

### Validation Rules

- Confirm the fetched document type matches the requested operation (`ACCREC` for invoices, Xero quotes only).
- Ensure the Xero contact matches the job client’s `xero_contact_id`. If not, return a descriptive 409.
- For quotes, block linking when the job already has a quote or when the Xero quote is linked elsewhere.
- For invoices, block linking if `invoice.job_id` is set to a different job; allow idempotent re-link if already attached to the same job.
- Require the job to be mutable (e.g., not archived) if business rules demand it—raise explicit TODO if additional policy emerges.

### Persistence & Side Effects

- Wrap linking in `transaction.atomic()` to keep the job + accounting record consistent.
- Update `quote.job` or `invoice.job` and `job.updated_at`, then save with constrained `update_fields`.
- For invoices, invoke `recalculate_job_invoicing_state(job.id)` after save.
- Insert a `JobEvent` documenting the linkage (`xero_quote_linked`, `xero_invoice_linked`) including identifiers inside `meta`.
- Return structured payloads (using existing serializers) so the frontend can refresh its state without refetching.

### Service Design

- Introduce `apps/job/services/xero_link_service.py` containing a `XeroDocumentLinkService` (or similar) that exposes:
  - `link_quote(job: Job, ref: str) -> Quote`
  - `link_invoice(job: Job, ref: str) -> Invoice`
  - Internal helpers for reference parsing, API fetch, validation, and persistence.
- Keep Xero API interaction encapsulated; inject an `AccountingApi` client to ease future testing/mocking.
- Ensure every exception path persists context via `persist_app_error`.

### API Surface

- Add `POST /job/rest/jobs/{job_id}/link-xero-quote/` and `POST /job/rest/jobs/{job_id}/link-xero-invoice/` endpoints under a new view module (e.g., `job_xero_link_views.py`).
- Define request serializers with fields:
  - `reference` (string, required): GUID or URL.
  - Optional `document_number` (string) for future enhancements.
- Use existing `QuoteSerializer` / `InvoiceSerializer` for responses to stay consistent.
- Register endpoints in `apps/job/urls_rest.py` (respecting kebab-case naming) and document with drf-spectacular (`extend_schema` annotations).

### Observability & Errors

- Add structured logging around link attempts (job id, document id, user id).
- Persist all unexpected exceptions to the app error table with operation metadata.
- Bubble validation issues as HTTP 400/409 with human-readable error messages to support quick operator triage.

### Documentation & Ops

- Update `docs/job-delta-frontend-integration.md` (backend considerations section) or create a focused guide under `docs/` describing the linking workflow and required payloads.
- Outline manual validation steps and failure recovery inside the docs update.
- Consider appending a short FAQ covering “where to find the Xero GUID” and conflict scenarios.

## Implementation Tasks

- [ ] **TASK-LINK-001** – Draft API contract + workflow notes for the frontend in `docs/` (include reference parsing rules and validation outcomes).
- [ ] **TASK-LINK-002** – Implement Xero GUID parsing + fetch helpers (invoice & quote) leveraging `AccountingApi` and existing transformers.
- [ ] **TASK-LINK-003** – Build `XeroDocumentLinkService` with validations, persistence, job event emission, and `updated_at` handling.
- [ ] **TASK-LINK-004** – Expose REST endpoints for quote/invoice linking, wiring serializers, permissions, drf-spectacular metadata, and service integration.
- [ ] **TASK-LINK-005** – Trigger `recalculate_job_invoicing_state` post-link and ensure responses return fresh serializer data.
- [ ] **TASK-LINK-006** – Add structured logging + `persist_app_error` coverage for all failure paths.
- [ ] **TASK-LINK-007** – Perform manual validation exercises (see below) and capture results in handoff notes.

## Manual Validation Checklist

- Link a Xero quote (via GUID + via full URL) to a job that has no quote; verify job detail shows the quote and a `JobEvent` is recorded.
- Attempt to re-link the same quote to the same job (should be idempotent) and to a different job (should return 409).
- Link a Xero invoice to a job with matching client and confirm `fully_invoiced` recalculates when the totals exceed `latest_actual`.
- Attempt to link an invoice whose contact differs from the job’s client and confirm the request is rejected with a descriptive message.
- Confirm job ETag (`updated_at`) changes after linking by comparing `If-None-Match` behaviour on job detail.
- Inspect logs/app error table to ensure telemetry is captured for both success and failure scenarios.

## Risks & Follow-Ups

- **Client mismatch edge cases** – Some historical jobs may lack a `xero_contact_id`; document that linking requires client sync and propose a follow-up to improve UX around this prerequisite.
- **Quote schema gaps** – We currently do not expose quote numbers; if operators need them surfaced, schedule a follow-up to extend serializers/models.
- **Bulk backfill need** – If multiple documents must be linked after a prolonged outage, consider a management command building on the same service (future work).
- Coordinate with the frontend team so they can surface clear success/failure feedback and guard against duplicate submissions.
