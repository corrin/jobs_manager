# Job Delta Integrity - Frontend Integration Guide

## Overview

The backend now expects every mutable job request to include a fully self-contained delta envelope. This document outlines how the Vue client (and any other callers) should construct, queue, and submit these deltas so that the backend can enforce checksum validation, prevent cross-job corruption, and record structured job events with undo support. Existing ETag handling (`If-Match`) remains mandatory and is assumed to be in place.

## Delta Envelope Contract

Every PATCH/POST that mutates a job must send a JSON payload in the following shape.

```json
{
  "change_id": "uuid-v4",
  "actor_id": "staff-uuid",
  "made_at": "2025-10-06T16:07:11.251Z",
  "job_id": "job-uuid",
  "fields": ["description", "order_number"],
  "before": {
    "description": "Cut and fold",
    "order_number": "PO-123"
  },
  "after": {
    "description": "",
    "order_number": "PO-123"
  },
  "before_checksum": "sha256(job_id|description=Cut and fold|order_number=PO-123)",
  "etag": "job:..."
}
```

### Canonicalisation Rules

- Compute `before_checksum` using the shared canonical function (mirrors `apps/job/services/delta_checksum.py`):
  - Sort field keys alphabetically.
  - Convert `None` to the literal string `"__NULL__"`.
  - Trim whitespace for string comparisons.
  - Serialise decimals using the backend precision (e.g., `Decimal('5.10')` -> `"5.10"`).
  - Concatenate as `"{job_id}|{field}={value}|..."`, then hash with SHA-256.
- `change_id` is an opaque UUID scoped to the delta queue; reuse the same ID for retries to avoid duplicate events.
- `made_at` uses ISO 8601 with millisecond precision and UTC (`Z`) suffix.

## Frontend Responsibilities

### 1. Maintain a Delta Queue

- Keep a per-job queue of pending changes ordered by the latest ETag returned from the backend.
- Each queue item stores the delta envelope, optimistic job snapshot, and retry metadata.
- Construct new deltas only from the most recent job snapshot (after applying earlier queued deltas locally).

### 2. Interaction Flow

1. **Fetch job** via GET. Capture `etag` and current field values.
2. **User edits** a field. Build `before` from the stored snapshot and `after` from the new value.
3. **Enqueue delta** with the freshly computed checksum and optimistic ETag (the one returned from the GET or the last successful PATCH).
4. **Submit sequentially**:
   - Pop the first delta.
   - Send PATCH with the envelope and an `If-Match: W/"job:..."` header.
   - Wait for success/failure before sending the next delta.
5. **On success (200/204)**:
   - Update the local job snapshot with `after`.
   - Replace the queue head with the next delta, updating their `etag` to the response header if present.
6. **On 412 Precondition Failed**:
   - Stop queue processing.
   - Trigger a refetch of the job (GET) to refresh state and ETag.
   - Rebuild deltas whose `before` no longer matches, prompting the user when their change conflicts.
7. **On validation errors (400/409)**:
   - Surface the backend message inline.
   - Allow the user to amend the delta and retry.

### 3. UI Feedback

- Surface conflict errors distinctly (e.g., "Job changed elsewhere - review updates before retrying").
- Show progress indicators while the queue flushes to prevent rapid successive edits from overwhelming the sequence.
- Display undo history once available (pull from the enhanced `JobEvent` endpoint).

### 4. Undo Support

- Fetch job events including `change_id`, `delta_before`, and `delta_after`.
- When the user selects "Undo", POST to `/job-rest/jobs/{job_id}/undo-change/` with the `change_id`.
- Refresh the job and reset the local queue after a successful undo to avoid conflicting state.

## Implementation Checklist

1. **Shared Utilities**
   - Port backend checksum canonicalisation to the frontend (TypeScript helper) and add targeted unit tests to guarantee parity.
2. **State Management**
   - Extend the job store/module to track `etag`, current snapshot, and delta queue.
   - Ensure every form component reads/writes through the store to preserve ordering.
3. **Networking Layer**
   - Introduce a `submitDelta(delta)` service that applies `If-Match`, sends the envelope, and handles 412 / 400 / 409 responses with specific actions.
   - Log rejected deltas with context for troubleshooting.
4. **Conflict UX**
   - Provide a modal or inline summary showing the user's change vs. the server's latest state.
   - Allow the user to reapply or discard their delta after reviewing differences.
5. **Undo UI**
   - Surface a timeline view highlighting undoable events.
   - Disable undo when the backend responds with conflict (e.g., later changes exist).
6. **QA & Release**
   - Follow the manual validation checklist: multi-tab editing, stale window retry, high-frequency edits, undo happy path, undo conflicts, and offline/online recovery.

## Coordination Notes

- The backend roadmap lives in `.kilocode/tasks/job_delta_integrity_plan.md`; keep both documents in sync as implementation details evolve.
- All integrations (CLI scripts, schedulers, etc.) must adopt the same envelope or route writes through backend services that construct it server-side.
- Continue to reference `docs/frontend-etag-optimistic-concurrency.md` for ETag semantics and ensure the queue respects those guarantees.
