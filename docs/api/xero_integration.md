# Xero Integration Guide

## SSE Stream

**Endpoint**: `GET /api/xero/sync-stream/?task_id=<uuid>`

**Headers**: `Accept: text/event-stream`

Example event payload:

```json
{
  "datetime": "2025-06-27T12:34:56Z",
  "severity": "info",
  "message": "string",
  "progress": 42
}
```

## Errors API

**List**: `GET /xero-errors/`

Response:

```json
[
  {
    "id": "uuid",
    "timestamp": "2025-06-27T12:00:00Z",
    "message": "Missing fields [...]",
    "data": { "missing_fields": [...] },
    "entity": "invoice",
    "reference_id": "xero-uuid",
    "kind": "Xero"
  }
]
```

**Detail**: `GET /xero-errors/<uuid>/`
