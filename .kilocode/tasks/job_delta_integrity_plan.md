# Job Delta Integrity & Undo Roadmap

## Context

Multiple staff have reported that job fields (name, description, notes, order numbers) occasionally mutate to values belonging to other jobs. The current optimistic concurrency layer already enforces `If-Match` headers keyed off `updated_at`, but the backend still enriches PATCH payloads before persisting, so stale or cross-job payloads can slip through. Job events merely store descriptive text and cannot support differential audit trails or undo operations.

## Objectives

- Guarantee that every state transition originates from an explicit, self-contained delta supplied by the caller.
- Reject payloads when the `before` state no longer matches the database, capturing full telemetry for investigation.
- Persist structured before/after deltas inside `JobEvent` records to unlock reliable "undo change" functionality.
- Lay the groundwork for replay tooling and cross-system reconciliation without blocking current workstreams.

## Non-Goals

- No frontend implementation in this roadmap (tracked separately in `docs/`).
- No attempt to diagnose the historical corruption root-cause beyond collecting richer telemetry.
- No automated test suite expansion beyond checksum helper coverage; manual validation remains the standard for this app.

## Architecture Direction

### Delta Payload Contract

- Introduce a versioned delta envelope that includes `change_id`, `actor_id`, `made_at`, `fields`, `before`, `after`, `before_checksum`, and the current `etag`.
- Canonicalise checksum inputs server-side (sorted keys, trimmed strings, consistent null handling) to avoid drift.
- Require the frontend (and any integration clients) to send this envelope for all mutable job endpoints.

### Service-Layer Validation

- Enhance `JobRestService.update_job` (and other mutators) to:
  - Recompute the checksum from the live database values for the requested fields.
  - Compare literal `before` values to guard against checksum collisions.
  - Reject on mismatch with `PreconditionFailed`, persisting a structured error via `persist_app_error`.
  - Record audit context (`change_id`, actor, source IP) in logs for observability.

### Persisted Delta Events

- Extend `JobEvent` with JSON fields (`delta_before`, `delta_after`), `delta_checksum`, `change_id`, and `schema_version`.
- Store the same payload the backend validated, enabling undo/replay.
- Migrate existing events with default values and backfill indexes on `change_id` for fast lookup.

### Undo Workflow

- Expose a new service and endpoint to revert a change by `change_id`.
- Undo implementation reuses the delta validator, swapping `before`/`after`, and writes a compensating event.
- Guard undo with permissions and sanity checks (e.g., refuse if newer unapplied deltas exist unless forced).

## Workstreams & Tasks

### Phase 1 - Foundation & Telemetry

- [ ] **TASK-BACK-001** - Document the delta contract and checksum rules within `apps/job/services/` docstrings and `docs/job-delta-frontend-integration.md` (backend section).
- [ ] **TASK-BACK-002** - Implement deterministic checksum utilities (`apps/job/services/delta_checksum.py`) with unit tests covering nulls, trimming, order, and decimal handling.
- [ ] **TASK-BACK-003** - Wire the new checksum + before/after validations into `JobRestService.update_job`, returning HTTP 412 on mismatches and logging all conflicts.
- [ ] **TASK-BACK-004** - Capture rejected envelopes in a dedicated model/table for forensic analysis (`JobDeltaRejection`), linked to `Job` and `Staff`.

### Phase 2 - Structured Job Events

- [ ] **TASK-BACK-005** - Create Django migration adding JSON fields (`delta_before`, `delta_after`), `delta_checksum`, `schema_version`, and `change_id` to `JobEvent`, with indexes + constraints.
- [ ] **TASK-BACK-006** - Update event creation in `JobRestService.update_job` to persist structured deltas alongside human-readable descriptions.
- [ ] **TASK-BACK-007** - Build serializers/view adjustments so `/job-rest/jobs/{id}/events` returns the new fields.
- [ ] **TASK-BACK-008** - Write backfill script (as another migration) to seed `schema_version` and migrate legacy events with placeholder deltas where possible.

### Phase 3 - Undo & Tooling

- [ ] **TASK-BACK-009** - Implement `JobDeltaUndoService` with atomic rollback logic, checksum revalidation, and conflict handling.
- [ ] **TASK-BACK-010** - Add `POST /job-rest/jobs/{job_id}/undo-change/` endpoint guarded by permissions and existing ETag validation.
- [ ] **TASK-BACK-011** - Extend logging/metrics (`log_performance`, structured logs) to track undo attempts, successes, and failures.
- [ ] **TASK-BACK-012** - Produce operational runbook entries (manual validation checklist, failure recovery steps) in `docs/operations/`.
- [ ] **TASK-BACK-013** - Manual verification pass following `.kilocode/rules/06-testing-quality-assurance.md`, including conflict scenarios and undo replay.

## Risks & Mitigations

- **Checksum Drift** - Frontend may implement hashing differently. Mitigate with shared canonicalisation rules and checksum helper tests shared across stacks.
- **Event Bloat** - Storing full deltas increases payload size; compression and schema versioning help manage storage. Review retention policies once telemetry is live.

## Dependencies & Follow-Up

- Coordination with frontend documented in `docs/job-delta-frontend-integration.md`.
- Align with Xero/webhook update flows to ensure background processes also submit envelopes or continue using guarded server-side pathways.
- Existing ETag requirements (`If-Match`) remain in force; this roadmap builds atop that infrastructure.
- Future enhancement: introduce dedicated `row_version` column for stronger versioning once the delta contract stabilises.
