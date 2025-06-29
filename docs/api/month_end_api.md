# Month-End API Guide

## Endpoints

### `GET /rest/month-end/`
Returns a JSON object with two keys:

- `jobs`: list of special jobs excluding the stock job
- `stock_job`: data about the stock job

Each job entry includes:

```
{
  "job_id": "UUID",
  "job_number": 123,
  "job_name": "name",
  "client_name": "client",
  "history": [
    {"date": "ISO", "total_hours": 0.0, "total_dollars": 0.0}
  ],
  "total_hours": 0.0,
  "total_dollars": 0.0
}
```

`stock_job` contains:

```
{
  "job_id": "UUID",
  "job_number": 1,
  "job_name": "Worker Admin",
  "history": [
    {"date": "ISO", "material_line_count": 0, "material_cost": 0.0}
  ]
}
```

### `POST /rest/month-end/`
Send a JSON body with job IDs to run month end:

```
{"job_ids": ["uuid1", "uuid2"]}
```

Response lists processed jobs and any errors:

```
{"processed": ["uuid1"], "errors": [["uuid2", "error message"]]}
```
