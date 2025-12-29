# CostLine Schema Validation Report

## Executive Summary

- Validation sweep surfaced **13 cost lines** where `kind` was stored as `adjust` even though their metadata clearly represented labour/time activity.
- Root cause: workshop staff sometimes selected a **custom “LABOUR CHARGE PER HOUR” item**  instead of using the timesheet shortcut (by the time the line was created we maybe didn't have the automatic kind inference, so they used as shortcut maybe?), but after adding type inference, the grid maybe unproperly casted the kinds to 'adjustment' after manual description change (trigger to the cast), and the backend persisted them as adjustments with a `meta.consumed_by` trail (because the line was originally created as a material line item, even though simulating a labour line). One additional entry started life as a true timesheet row but was later misinterpreted by the front-end grid and saved as an adjustment.
- Data fix: migration `0061_fix_labour_cost_lines` now **casts any adjustment line containing labour/time metadata to `kind='time'`** so the new JSON schema passes and CostSet hour totals remain accurate.

## Data Fix Plan

1. Apply the new migration during deploy (it loops through adjustment lines and resaves the ones that carry labour/time metadata so summaries stay consistent).
2. Re-run the validation helper (`poetry run python - <<'PY' `) to confirm the offender list is empty after migration.
3. Keep this document for historical context; the table below reflects the snapshot **before** the migration ran.

## Front-end & Debug Follow-ups

1. **Timesheet grid safeguards:** when a user edits a time line’s description or toggles item mode, never reclassify the line purely based on description or SKU; persist the original `kind` unless the user explicitly changes the type selector.
2. **Item picker restrictions:** hide or flag catalogue items that actually represent labour so workshop staff are forced through the proper time-entry flow (or auto-convert such selections into `kind='time'` client-side).
3. **Debug endpoint:** expose a small admin/debug API (e.g., `/api/debug/cost-lines/?kind=adjust&has_meta=consumed_by`) so support can quickly list suspicious entries without shell access.

## Detailed Offenders (pre-fix snapshot)

> Each record below failed schema validation prior to the migration. Use it only as a reference; the migration reclassifies all of these lines.

Total failing cost lines before migration: 13

### Validation REPL Script

Run this snippet inside `poetry run python manage.py shell`

```python
import json
from django.core.exceptions import ValidationError
from apps.job.models import CostLine
from apps.job.models.costline_validators import (
    validate_costline_ext_refs,
    validate_costline_meta,
)

issues = []
qs = CostLine.objects.all().only(
    "id",
    "kind",
    "desc",
    "meta",
    "ext_refs",
    "cost_set_id",
    "accounting_date",
    "created_at",
    "updated_at",
)
for line in qs.iterator():
    try:
        validate_costline_meta(line.meta, line.kind)
        validate_costline_ext_refs(line.ext_refs)
    except ValidationError as exc:
        issues.append(
            {
                "id": str(line.id),
                "kind": line.kind,
                "desc": line.desc,
                "errors": exc.message_dict,
                "meta": line.meta,
                "ext_refs": line.ext_refs,
                "cost_set_id": str(line.cost_set_id),
                "accounting_date": line.accounting_date.isoformat()
                if line.accounting_date
                else None,
                "created_at": line.created_at.isoformat() if line.created_at else None,
                "updated_at": line.updated_at.isoformat() if line.updated_at else None,
            }
        )

print(f"Found {len(issues)} invalid cost lines")
print(json.dumps(issues, indent=2))
```

## 1. CostLine 7d8dc600-fa70-4f1d-b1cc-51ca7d99294c

- Kind: `adjust`

- Description: LABOUR CHARGE PER HOUR ADMIN

- Cost Set ID: `966dfc3b-953b-486d-acfc-1fee83ce3daf`

- Accounting Date: `2025-11-20`

- Created At: `2025-11-20T23:22:36+00:00`

- Updated At: `2025-11-20T23:22:44+00:00`

- Errors:

```json
{
  "meta": [
    "Additional properties are not allowed ('consumed_by' was unexpected) (path: .)"
  ]
}
```

- Meta contents:

```json
{
  "consumed_by": "d335acd4-800e-517a-8ff4-ba7aada58d14"
}
```

- Ext refs contents:

```json
{
  "stock_id": "fd0ee1a5-3b0c-48c3-a475-74385149fab1"
}
```

## 2. CostLine 2d1197fc-e92f-4375-adaa-5dbfdd25c4aa

- Kind: `adjust`

- Description: LABOUR CHARGE PER HOUR BEN UNDERSETIMATED TIME TAKEN AND DID NOT DISCUSS WITH PAUL

- Cost Set ID: `2d964c20-d571-4de8-b20a-ac57f0febbc2`

- Accounting Date: `2025-11-19`

- Created At: `2025-11-19T23:53:38+00:00`

- Updated At: `2025-11-19T23:54:27+00:00`

- Errors:

```json
{
  "meta": [
    "Additional properties are not allowed ('consumed_by' was unexpected) (path: .)"
  ]
}
```

- Meta contents:

```json
{
  "consumed_by": "d335acd4-800e-517a-8ff4-ba7aada58d14"
}
```

- Ext refs contents:

```json
{
  "stock_id": "fd0ee1a5-3b0c-48c3-a475-74385149fab1"
}
```

## 3. CostLine 3005bb8e-5549-44cb-bdbb-01eb580ba020

- Kind: `adjust`

- Description: LABOUR CHARGE PER HOUR OVER TIME

- Cost Set ID: `d7518126-3be5-4ff9-86a3-9a6eb0ac7e02`

- Accounting Date: `2025-11-19`

- Created At: `2025-11-19T22:17:31+00:00`

- Updated At: `2025-11-19T22:17:43+00:00`

- Errors:

```json
{
  "meta": [
    "Additional properties are not allowed ('consumed_by' was unexpected) (path: .)"
  ]
}
```

- Meta contents:

```json
{
  "consumed_by": "d335acd4-800e-517a-8ff4-ba7aada58d14"
}
```

- Ext refs contents:

```json
{
  "stock_id": "fd0ee1a5-3b0c-48c3-a475-74385149fab1"
}
```

## 4. CostLine 8283f2e9-e0f4-46ef-87d0-338c1e6ebcda

- Kind: `adjust`

- Description: LABOUR CHARGE PER HOUR

- Cost Set ID: `5f02af9c-7032-4dc4-9e9e-2c53c8167436`

- Accounting Date: `2025-11-17`

- Created At: `2025-11-17T23:34:00+00:00`

- Updated At: `2025-11-17T23:34:12+00:00`

- Errors:

```json
{
  "meta": [
    "Additional properties are not allowed ('consumed_by' was unexpected) (path: .)"
  ]
}
```

- Meta contents:

```json
{
  "consumed_by": "d335acd4-800e-517a-8ff4-ba7aada58d14"
}
```

- Ext refs contents:

```json
{
  "stock_id": "fd0ee1a5-3b0c-48c3-a475-74385149fab1"
}
```

## 5. CostLine bfc1df11-f4cc-47f4-8392-22b3d799c00f

- Kind: `adjust`

- Description: LABOUR CHARGE PER HOUR OVER TIME

- Cost Set ID: `3eec2a18-129f-4bd8-ba88-e9ae207a887e`

- Accounting Date: `2025-11-13`

- Created At: `2025-11-13T00:41:46+00:00`

- Updated At: `2025-11-13T00:41:57+00:00`

- Errors:

```json
{
  "meta": [
    "Additional properties are not allowed ('consumed_by' was unexpected) (path: .)"
  ]
}
```

- Meta contents:

```json
{
  "consumed_by": "d335acd4-800e-517a-8ff4-ba7aada58d14"
}
```

- Ext refs contents:

```json
{
  "stock_id": "fd0ee1a5-3b0c-48c3-a475-74385149fab1"
}
```

## 6. CostLine 3a980a8b-1d7e-41ec-8a55-daefa19f53ad

- Kind: `adjust`

- Description: LABOUR CHARGE PER HOUR ADJUSTEMENT

- Cost Set ID: `3eec2a18-129f-4bd8-ba88-e9ae207a887e`

- Accounting Date: `2025-11-13`

- Created At: `2025-11-13T00:40:55+00:00`

- Updated At: `2025-11-13T00:41:10+00:00`

- Errors:

```json
{
  "meta": [
    "Additional properties are not allowed ('consumed_by' was unexpected) (path: .)"
  ]
}
```

- Meta contents:

```json
{
  "consumed_by": "d335acd4-800e-517a-8ff4-ba7aada58d14"
}
```

- Ext refs contents:

```json
{
  "stock_id": "fd0ee1a5-3b0c-48c3-a475-74385149fab1"
}
```

## 7. CostLine a2ba6c6d-e43e-40a6-886f-fe80a60c7efb

- Kind: `adjust`

- Description: LABOUR CHARGE PER HOUR ADMIN TIME

- Cost Set ID: `54667662-ea7c-4013-92af-2d1afbdb35f8`

- Accounting Date: `2025-11-12`

- Created At: `2025-11-12T19:21:23+00:00`

- Updated At: `2025-11-12T19:21:45+00:00`

- Errors:

```json
{
  "meta": [
    "Additional properties are not allowed ('consumed_by' was unexpected) (path: .)"
  ]
}
```

- Meta contents:

```json
{
  "consumed_by": "d335acd4-800e-517a-8ff4-ba7aada58d14"
}
```

- Ext refs contents:

```json
{
  "stock_id": "fd0ee1a5-3b0c-48c3-a475-74385149fab1"
}
```

## 8. CostLine cf93c801-8a9e-4ac9-8d08-35d141602433

- Kind: `adjust`

- Description: LABOUR CHARGE PER HOUR ADMIN

- Cost Set ID: `5f76381e-0c2b-475b-ace7-c34de639154b`

- Accounting Date: `2025-10-30`

- Created At: `2025-10-30T19:21:13+00:00`

- Updated At: `2025-10-30T19:21:28+00:00`

- Errors:

```json
{
  "meta": [
    "Additional properties are not allowed ('consumed_by' was unexpected) (path: .)"
  ]
}
```

- Meta contents:

```json
{
  "consumed_by": "d335acd4-800e-517a-8ff4-ba7aada58d14"
}
```

- Ext refs contents:

```json
{
  "stock_id": "fd0ee1a5-3b0c-48c3-a475-74385149fab1"
}
```

## 9. CostLine f5d68864-c5ab-4e09-9297-d285f91fb9fe

- Kind: `adjust`

- Description: DRAW AND LASER PARTS - - ADDITIONAL TIME DUE TO CUSTOMER AMENDMENT

- Cost Set ID: `65557722-6419-4e8d-ab57-be82116e5e43`

- Accounting Date: `2025-10-29`

- Created At: `2025-10-28T22:47:04+00:00`

- Updated At: `2025-10-28T22:47:54+00:00`

- Errors:

```json
{
  "meta": [
    "Additional properties are not allowed ('created_from_timesheet', 'date', 'is_billable', 'rate_multiplier', 'staff_id' were unexpected) (path: .)"
  ]
}
```

- Meta contents:

```json
{
  "created_from_timesheet": true,
  "date": "2025-10-29",
  "is_billable": true,
  "rate_multiplier": 1,
  "staff_id": "f8922656-5227-55dd-96f3-9d9bde0376c9"
}
```

- Ext refs contents:

```json
{}
```

## 10. CostLine 5da59ccf-ecd2-4554-8be4-6f6e7c5537b0

- Kind: `adjust`

- Description: LABOUR CHARGE PER HOUR

- Cost Set ID: `a867f6d6-5ac8-436c-8b80-552318383501`

- Accounting Date: `2025-10-28`

- Created At: `2025-10-28T20:16:45+00:00`

- Updated At: `2025-10-28T20:18:11+00:00`

- Errors:

```json
{
  "meta": [
    "Additional properties are not allowed ('consumed_by' was unexpected) (path: .)"
  ]
}
```

- Meta contents:

```json
{
  "consumed_by": "d335acd4-800e-517a-8ff4-ba7aada58d14"
}
```

- Ext refs contents:

```json
{
  "stock_id": "fd0ee1a5-3b0c-48c3-a475-74385149fab1"
}
```

## 11. CostLine 9e621ad4-0f7d-41dc-b2c8-c8eb128ee110

- Kind: `adjust`

- Description: Consumed: LABOUR CHARGE PER HOUR

- Cost Set ID: `4b2b3f79-9b29-47c7-a552-592ff9ec8402`

- Accounting Date: `2025-10-14`

- Created At: `2025-10-14T22:08:31+00:00`

- Updated At: `2025-10-14T22:08:59+00:00`

- Errors:

```json
{
  "meta": [
    "Additional properties are not allowed ('consumed_by' was unexpected) (path: .)"
  ]
}
```

- Meta contents:

```json
{
  "consumed_by": "d335acd4-800e-517a-8ff4-ba7aada58d14"
}
```

- Ext refs contents:

```json
{
  "stock_id": "fd0ee1a5-3b0c-48c3-a475-74385149fab1"
}
```

## 12. CostLine 67cd4634-4606-4bac-b7c4-fd3bbc3a135f

- Kind: `adjust`

- Description: Consumed: LABOUR CHARGE PER HOUR ALEX UINDER QUOTED TIME ALLOWED

- Cost Set ID: `4d331717-6c28-4024-979e-e9d40506ea08`

- Accounting Date: `2025-10-12`

- Created At: `2025-10-12T21:47:27+00:00`

- Updated At: `2025-10-12T21:49:12+00:00`

- Errors:

```json
{
  "meta": [
    "Additional properties are not allowed ('consumed_by' was unexpected) (path: .)"
  ]
}
```

- Meta contents:

```json
{
  "consumed_by": "d335acd4-800e-517a-8ff4-ba7aada58d14"
}
```

- Ext refs contents:

```json
{
  "stock_id": "fd0ee1a5-3b0c-48c3-a475-74385149fab1"
}
```

## 13. CostLine 77195c6f-f3ea-46ef-b8f6-4d60bbe405e8

- Kind: `adjust`

- Description: Consumed: LABOUR CHARGE PER HOUR

- Cost Set ID: `81496b8c-8b85-46aa-888a-56e43e303a6d`

- Accounting Date: `2025-10-09`

- Created At: `2025-10-09T20:06:24+00:00`

- Updated At: `2025-10-09T20:06:41+00:00`

- Errors:

```json
{
  "meta": [
    "Additional properties are not allowed ('consumed_by' was unexpected) (path: .)"
  ]
}
```

- Meta contents:

```json
{
  "consumed_by": "d335acd4-800e-517a-8ff4-ba7aada58d14"
}
```

- Ext refs contents:

```json
{
  "stock_id": "fd0ee1a5-3b0c-48c3-a475-74385149fab1"
}
```
